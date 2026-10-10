from __future__ import annotations

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from starlette.testclient import TestClient

from helpers import make_brief, make_signal
from signalgraph.mcp_server import mcp, scan_trends_tool
from signalgraph.models import TrackResearchResult
from signalgraph.sites_backend import RESEARCH_ONLY_OVERRIDES, create_app

TOKEN = "synthetic-backend-token-0123456789"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2025-11-25",
}


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(TOKEN, tmp_path), base_url="http://127.0.0.1:8000") as client:
        yield client


def rpc(client, method, params=None, **kwargs):
    return client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
        headers=HEADERS,
        **kwargs,
    )


def result(response):
    assert response.status_code == 200, response.text
    assert "mcp-session-id" not in response.headers
    messages = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ") and line[6:].strip()
    ]
    return next(message for message in messages if message.get("id") == 1)


def test_discovery_matches_existing_surface_and_bounds(client):
    init = result(
        rpc(
            client,
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "fixture", "version": "1"},
            },
        )
    )
    assert init["result"]["protocolVersion"] == "2025-11-25"
    tools = result(rpc(client, "tools/list"))["result"]["tools"]
    local = asyncio.run(mcp.list_tools())
    assert [tool["name"] for tool in tools] == [tool.name for tool in local]
    schema = tools[0]["inputSchema"]["properties"]
    assert schema.keys() == local[0].inputSchema["properties"].keys()
    assert tools[0].get("outputSchema") == local[0].outputSchema
    assert schema["max_parallel"]["maximum"] == 5
    assert schema["max_signals"]["maximum"] == 40
    assert tools[0]["annotations"]["readOnlyHint"] is True
    notification = client.post(
        "/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=HEADERS
    )
    assert notification.status_code == 202 and not notification.content
    assert "result" in result(rpc(client, "ping"))


def test_scan_uses_existing_graph_and_preserves_output(client, monkeypatch, tmp_path):
    calls = []

    async def research(**kwargs):
        calls.append(kwargs)
        return [TrackResearchResult(track="oss", summary="fixture", signals=[make_signal()])]

    monkeypatch.setattr("signalgraph.graph.research_tracks_with_codex", research)
    remote = result(
        rpc(client, "tools/call", {"name": "scan_trends_tool", "arguments": {"theme": "AI agents"}})
    )["result"]
    assert not remote.get("isError", False)
    brief = json.loads(remote["content"][0]["text"])
    assert brief == asyncio.run(scan_trends_tool("AI agents"))
    assert brief["committed_signals"][0]["source_url"] == "https://example.com/signal"
    assert calls[0]["repo"] == str(tmp_path.resolve())
    assert calls[0]["codex_config_overrides"] == RESEARCH_ONLY_OVERRIDES
    assert len(calls[0]["tracks"]) == 5
    assert all(
        track.max_findings == 8 and track.min_candidates == 15 for track in calls[0]["tracks"]
    )


@pytest.mark.parametrize(
    "arguments",
    [
        {"repo": "C:/private"},
        {"codex_config_overrides": ['sandbox_mode="danger-full-access"']},
        {"max_parallel": 0},
        {"max_parallel": 6},
        {"max_parallel": True},
        {"max_signals": 41},
        {"theme": " "},
        {"theme": "a" * 2001},
        {"language": "fr"},
        {"web_search": "other"},
    ],
)
def test_restricted_inputs_never_execute(client, monkeypatch, arguments):
    async def forbidden(*args, **kwargs):
        pytest.fail("invalid input reached the graph")

    monkeypatch.setattr("signalgraph.sites_backend.scan_trends", forbidden)
    response = result(
        rpc(
            client,
            "tools/call",
            {"name": "scan_trends_tool", "arguments": {"theme": "AI agents", **arguments}},
        )
    )
    assert response["result"]["isError"] is True


def test_failure_is_a_redacted_tool_error(client, monkeypatch):
    async def broken(*args, **kwargs):
        raise RuntimeError("private-path-and-secret")

    monkeypatch.setattr("signalgraph.sites_backend.scan_trends", broken)
    response = rpc(
        client, "tools/call", {"name": "scan_trends_tool", "arguments": {"theme": "AI agents"}}
    )
    payload = result(response)["result"]
    assert payload["isError"] is True
    assert "private-path-and-secret" not in response.text
    assert "operator" in payload["content"][0]["text"]


def test_timeout_is_bounded(client, monkeypatch):
    async def slow(*args, **kwargs):
        await asyncio.sleep(10)
        return make_brief()

    monkeypatch.setattr("signalgraph.sites_backend.SCAN_TIMEOUT", 0.01)
    monkeypatch.setattr("signalgraph.sites_backend.scan_trends", slow)
    payload = result(
        rpc(client, "tools/call", {"name": "scan_trends_tool", "arguments": {"theme": "AI agents"}})
    )["result"]
    assert payload["isError"] is True
    assert "timed out" in payload["content"][0]["text"]


def test_busy_backend_rejects_concurrent_scan_and_releases_lock(client, monkeypatch):
    started = threading.Event()
    release = threading.Event()

    async def slow(*args, **kwargs):
        started.set()
        await asyncio.to_thread(release.wait, 5)
        return make_brief()

    monkeypatch.setattr("signalgraph.sites_backend.scan_trends", slow)
    params = {"name": "scan_trends_tool", "arguments": {"theme": "AI agents"}}
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(rpc, client, "tools/call", params)
        try:
            assert started.wait(5)
            busy = result(rpc(client, "tools/call", params))["result"]
            assert busy["isError"] is True
            assert "busy" in busy["content"][0]["text"]
        finally:
            release.set()
        assert not result(first.result(timeout=5))["result"].get("isError", False)
    assert not result(rpc(client, "tools/call", params))["result"].get("isError", False)


def test_http_auth_origin_methods_size_and_protocol(client):
    assert client.post("/mcp").status_code == 401
    assert (
        client.post("/mcp", headers={**HEADERS, "Authorization": "Bearer bad"}).status_code == 401
    )
    assert (
        client.post("/mcp", headers={**HEADERS, "Origin": "https://evil.example"}).status_code
        == 403
    )
    assert (
        client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
            headers={**HEADERS, "Host": "evil.example"},
        ).status_code
        == 421
    )
    assert client.get("/mcp", headers=HEADERS).status_code == 405
    assert client.post("/other", headers=HEADERS).status_code == 404
    assert client.post("/mcp", content="x" * 16385, headers=HEADERS).status_code == 413
    assert client.post("/mcp", content="not json", headers=HEADERS).status_code == 400
    assert (
        client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
            headers={**HEADERS, "MCP-Protocol-Version": "unsupported"},
        ).status_code
        == 400
    )
    assert (
        rpc(
            client,
            "tools/call",
            {"name": "scan_trends_tool", "arguments": {"theme": "test", "shell": "bad"}},
        ).status_code
        == 400
    )
    assert "error" in result(rpc(client, "unknown/method"))


def test_startup_requires_private_directory_and_token(tmp_path):
    with pytest.raises(ValueError, match="token"):
        create_app("short", tmp_path)
    (tmp_path / "private-file").write_text("fixture")
    with pytest.raises(ValueError, match="empty"):
        create_app(TOKEN, tmp_path)


def test_main_removes_service_secrets_from_child_environment(monkeypatch, tmp_path):
    from signalgraph.sites_backend import main

    monkeypatch.setenv("SIGNALGRAPH_BACKEND_TOKEN", TOKEN)
    monkeypatch.setenv("SIGNALGRAPH_RESEARCH_DIR", str(tmp_path))

    def fake_run(*args, **kwargs):
        import os

        assert "SIGNALGRAPH_BACKEND_TOKEN" not in os.environ
        assert "SIGNALGRAPH_RESEARCH_DIR" not in os.environ
        assert kwargs == {"host": "127.0.0.1", "port": 8000, "access_log": False}

    monkeypatch.setattr("uvicorn.run", fake_run)
    main()

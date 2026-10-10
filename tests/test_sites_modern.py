"""Actual adapter responses for MCP 2026-07-28; research remains mocked."""

from __future__ import annotations

import asyncio
import base64
import json

import pytest
from starlette.testclient import TestClient

from helpers import make_brief
from signalgraph.sites_backend import create_app

TOKEN = "synthetic-modern-token-0123456789"
VERSION = "2026-07-28"
PREFIX = "io.modelcontextprotocol/"


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(TOKEN, tmp_path), base_url="http://127.0.0.1:8000") as client:
        yield client


def modern(client, method, params=None, *, meta=None, headers=None):
    params = dict(params or {})
    params["_meta"] = (
        meta
        if meta is not None
        else {
            PREFIX + "protocolVersion": VERSION,
            PREFIX + "clientCapabilities": {},
            PREFIX + "clientInfo": {"name": "fixture", "version": "1"},
        }
    )
    mirrors = {"Mcp-Method": method, "MCP-Protocol-Version": VERSION}
    if method == "tools/call":
        mirrors["Mcp-Name"] = params.get("name", "")
    return client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": "modern-1", "method": method, "params": params},
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json, text/event-stream",
            **mirrors,
            **(headers or {}),
        },
    )


def payload(response):
    assert response.status_code == 200, response.text
    assert "mcp-session-id" not in response.headers
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return next(
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ") and line[6:].strip()
    )


def test_modern_discovery_and_empty_sites_bootstrap_probe(client):
    response = payload(modern(client, "server/discover"))
    result = response["result"]
    assert response["id"] == "modern-1"
    assert result["resultType"] == "complete"
    assert VERSION in result["supportedVersions"] and "2025-11-25" in result["supportedVersions"]
    assert result["capabilities"] == {"tools": {}}
    assert result["_meta"][PREFIX + "serverInfo"] == {"name": "signalgraph", "version": "0.1.0"}
    assert result["ttlMs"] == 0 and result["cacheScope"] == "private"
    probe = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 0, "method": "server/discover", "params": {}},
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json, text/event-stream",
        },
    )
    assert payload(probe)["result"] == result
    missing = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 0, "method": "server/discover"},
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json, text/event-stream",
        },
    )
    assert missing.status_code == 400 and missing.json()["error"]["code"] == -32602


def test_modern_list_and_call_share_legacy_tool_output(client, monkeypatch):
    calls = []

    async def research(theme, config):
        calls.append((theme, config))
        return make_brief()

    monkeypatch.setattr("signalgraph.sites_backend.scan_trends", research)
    listed = payload(modern(client, "tools/list"))["result"]
    assert listed["resultType"] == "complete"
    assert listed["ttlMs"] == 0 and listed["cacheScope"] == "private"
    assert [tool["name"] for tool in listed["tools"]] == ["scan_trends_tool"]
    result = payload(
        modern(
            client, "tools/call", {"name": "scan_trends_tool", "arguments": {"theme": "AI agents"}}
        )
    )["result"]
    assert result["resultType"] == "complete" and not result["isError"]
    assert json.loads(result["content"][0]["text"]) == make_brief().model_dump()
    assert len(calls) == 1 and calls[0][1].repo != "."
    assert payload(modern(client, "ping"))["result"]["resultType"] == "complete"


@pytest.mark.parametrize(
    "meta,headers,code",
    [
        ({PREFIX + "protocolVersion": VERSION}, {}, -32602),
        ({PREFIX + "protocolVersion": VERSION, PREFIX + "clientCapabilities": []}, {}, -32602),
        (
            {PREFIX + "protocolVersion": VERSION, PREFIX + "clientCapabilities": {"roots": False}},
            {},
            -32602,
        ),
        (
            {
                PREFIX + "protocolVersion": VERSION,
                PREFIX + "clientCapabilities": {},
                PREFIX + "clientInfo": {},
            },
            {},
            -32602,
        ),
        (
            {PREFIX + "protocolVersion": "1900-01-01", PREFIX + "clientCapabilities": {}},
            {"MCP-Protocol-Version": "1900-01-01"},
            -32022,
        ),
        (
            {PREFIX + "protocolVersion": "1900-01-01", PREFIX + "clientCapabilities": {}},
            {"MCP-Protocol-Version": "2025-11-25"},
            -32020,
        ),
        (
            {PREFIX + "protocolVersion": VERSION, PREFIX + "clientCapabilities": {}},
            {"MCP-Protocol-Version": "2025-11-25"},
            -32020,
        ),
        (
            {PREFIX + "protocolVersion": VERSION, PREFIX + "clientCapabilities": {}},
            {"Mcp-Method": "tools/call"},
            -32020,
        ),
        (
            {PREFIX + "protocolVersion": VERSION, PREFIX + "clientCapabilities": {}},
            {"Mcp-Method": "\t"},
            -32020,
        ),
    ],
)
def test_metadata_errors_are_modern_rpc_errors(client, meta, headers, code):
    response = modern(client, "tools/list", meta=meta, headers=headers)
    assert response.status_code == 400
    error = response.json()
    assert error["id"] == "modern-1" and error["error"]["code"] == code
    if code == -32022:
        assert VERSION in error["error"]["data"]["supported"]
        assert error["error"]["data"]["requested"] == "1900-01-01"


@pytest.mark.parametrize(
    "arguments",
    [
        {"repo": "C:/private"},
        {"codex_config_overrides": ["features.shell_tool=true"]},
        {"max_parallel": 6},
        {"max_parallel": True},
        {"theme": "a" * 2001},
        {"shell": "bad"},
    ],
)
def test_modern_invalid_arguments_never_execute(client, monkeypatch, arguments):
    async def forbidden(*args, **kwargs):
        pytest.fail("invalid modern arguments reached research")

    monkeypatch.setattr("signalgraph.sites_backend.scan_trends", forbidden)
    response = modern(
        client,
        "tools/call",
        {"name": "scan_trends_tool", "arguments": {"theme": "AI agents", **arguments}},
    )
    assert response.status_code == 400 and response.json()["error"]["code"] == -32602


def test_name_headers_unknown_methods_and_cursors(client, monkeypatch):
    async def research(*args, **kwargs):
        return make_brief()

    monkeypatch.setattr("signalgraph.sites_backend.scan_trends", research)
    params = {"name": "scan_trends_tool", "arguments": {"theme": "AI agents"}}
    encoded = "=?base64?" + base64.b64encode(b"scan_trends_tool").decode() + "?="
    assert not payload(modern(client, "tools/call", params, headers={"Mcp-Name": encoded}))[
        "result"
    ]["isError"]
    for name in ["other", "", "=?base64?!!!?="]:
        response = modern(client, "tools/call", params, headers={"Mcp-Name": name})
        assert response.status_code == 400 and response.json()["error"]["code"] == -32020
    response = modern(
        client,
        "resources/read",
        {"uri": "file:///private"},
        headers={"Mcp-Name": "file:///private"},
    )
    assert response.status_code == 404 and response.json()["error"]["code"] == -32601
    response = modern(client, "resources/read", {"uri": "file:///private"})
    assert response.status_code == 400 and response.json()["error"]["code"] == -32020
    for method, values in [
        ("tools/list", {"cursor": "invalid"}),
        ("ping", {"extra": 1}),
        ("server/discover", {"extra": 1}),
        ("tools/call", {**params, "requestState": "unsupported"}),
        ("tools/call", {"name": "unknown", "arguments": {}}),
    ]:
        response = modern(client, method, values)
        assert response.status_code == 400 and response.json()["error"]["code"] == -32602


def test_modern_failures_auth_and_invalid_envelope(client, monkeypatch):
    async def broken(*args, **kwargs):
        raise RuntimeError("private-credential-and-path")

    monkeypatch.setattr("signalgraph.sites_backend.scan_trends", broken)
    response = modern(
        client, "tools/call", {"name": "scan_trends_tool", "arguments": {"theme": "AI agents"}}
    )
    assert payload(response)["result"]["isError"] is True
    assert "private-credential-and-path" not in response.text
    assert (
        modern(client, "server/discover", headers={"Authorization": "Bearer wrong"}).status_code
        == 401
    )
    assert modern(client, "server/discover", headers={"Host": "evil.example"}).status_code == 421
    assert (
        modern(client, "server/discover", headers={"Origin": "https://evil.example"}).status_code
        == 403
    )
    assert modern(client, "ping", headers={"Accept": "application/json"}).status_code == 406
    probe = {"jsonrpc": "2.0", "id": True, "method": "server/discover", "params": {}}
    response = client.post("/mcp", json=probe, headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 400 and response.json()["error"]["code"] == -32600


@pytest.mark.parametrize("message", [None, [], [{"jsonrpc": "2.0", "id": 1, "method": "ping"}]])
def test_modern_nonobject_envelopes_are_rpc_errors(client, message):
    response = client.post(
        "/mcp",
        content=json.dumps(message),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": VERSION,
        },
    )
    assert response.status_code == 400
    assert response.json() == {
        "jsonrpc": "2.0",
        "id": None,
        "error": {"code": -32600, "message": "Invalid JSON-RPC request"},
    }


def test_modern_disconnect_cancels_research_and_releases_admission(tmp_path, monkeypatch):
    async def exercise():
        app = create_app(TOKEN, tmp_path)
        started, disconnected, cancelled = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def research(*args, **kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        monkeypatch.setattr("signalgraph.sites_backend.scan_trends", research)
        params = {
            "name": "scan_trends_tool",
            "arguments": {"theme": "AI agents"},
            "_meta": {
                PREFIX + "protocolVersion": VERSION,
                PREFIX + "clientCapabilities": {},
            },
        }
        body = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}
        ).encode()
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "path": "/mcp",
            "raw_path": b"/mcp",
            "query_string": b"",
            "scheme": "http",
            "server": ("127.0.0.1", 8000),
            "client": ("127.0.0.1", 1),
            "headers": [
                (b"host", b"127.0.0.1:8000"),
                (b"authorization", f"Bearer {TOKEN}".encode()),
                (b"accept", b"application/json, text/event-stream"),
                (b"content-type", b"application/json"),
                (b"mcp-protocol-version", VERSION.encode()),
                (b"mcp-method", b"tools/call"),
                (b"mcp-name", b"scan_trends_tool"),
            ],
        }
        sent = False

        async def receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            await disconnected.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            pass

        task = asyncio.create_task(app(scope, receive, send))
        try:
            await asyncio.wait_for(started.wait(), 5)
            disconnected.set()
            await asyncio.wait_for(task, 5)
            assert cancelled.is_set()
        finally:
            task.cancel()

        # The same app's lock must permit a later request after cancellation.
        async def quick(*args, **kwargs):
            return make_brief()

        monkeypatch.setattr("signalgraph.sites_backend.scan_trends", quick)
        with TestClient(app, base_url="http://127.0.0.1:8000") as client:
            assert not payload(
                modern(
                    client,
                    "tools/call",
                    {"name": "scan_trends_tool", "arguments": {"theme": "AI agents"}},
                )
            )["result"]["isError"]

    asyncio.run(exercise())

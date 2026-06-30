from __future__ import annotations

import asyncio
import json

from typer.testing import CliRunner

from signalgraph.cli import app
from signalgraph.mcp_server import scan_trends_tool
from helpers import make_brief


def test_cli_scan_writes_markdown(monkeypatch, tmp_path) -> None:
    async def fake_scan_trends(theme, config):
        assert theme == "AI agents"
        assert config.max_parallel == 2
        return make_brief()

    monkeypatch.setattr("signalgraph.cli.scan_trends", fake_scan_trends)
    out = tmp_path / "brief.md"

    result = CliRunner().invoke(
        app,
        ["scan", "AI agents", "--max-parallel", "2", "--out", str(out)],
    )

    assert result.exit_code == 0
    assert "SignalGraph Brief" in out.read_text(encoding="utf-8")


def test_cli_scan_prints_json(monkeypatch) -> None:
    async def fake_scan_trends(theme, config):
        return make_brief()

    monkeypatch.setattr("signalgraph.cli.scan_trends", fake_scan_trends)

    result = CliRunner().invoke(app, ["scan", "AI agents", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["theme"] == "AI agents"


def test_cli_scan_reports_bad_theme(monkeypatch) -> None:
    async def fake_scan_trends(theme, config):
        raise ValueError("theme must not be empty")

    monkeypatch.setattr("signalgraph.cli.scan_trends", fake_scan_trends)

    result = CliRunner().invoke(app, ["scan", " "])

    assert result.exit_code != 0
    assert "theme must not be empty" in result.output


def test_mcp_tool_returns_brief_dict(monkeypatch) -> None:
    async def fake_scan_trends(theme, config):
        assert theme == "AI agents"
        assert config.codex_config_overrides == ("foo=1",)
        return make_brief()

    monkeypatch.setattr("signalgraph.mcp_server.scan_trends", fake_scan_trends)

    payload = asyncio.run(
        scan_trends_tool(
            "AI agents",
            max_signals=3,
            codex_config_overrides=["foo=1"],
        )
    )

    assert payload["theme"] == "AI agents"
    assert payload["committed_signals"][0]["title"] == "Example Signal"

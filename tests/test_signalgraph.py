from __future__ import annotations

import asyncio

from signalgraph.core import render_markdown, scan_trends
from signalgraph.models import (
    SignalGraphConfig,
    TrackResearchResult,
)
from helpers import make_brief, make_signal


def test_scan_trends_uses_graph_and_deduplicates(monkeypatch) -> None:
    async def fake_research_tracks_with_codex(**kwargs):
        return [
            TrackResearchResult(
                track="oss",
                summary="OSS track",
                signals=[
                    make_signal("A", "https://example.com/a"),
                    make_signal("A duplicate", "https://example.com/a"),
                    make_signal("B", "https://example.com/b", action="quarantine"),
                ],
            )
        ]

    monkeypatch.setattr(
        "signalgraph.graph.research_tracks_with_codex",
        fake_research_tracks_with_codex,
    )

    brief = asyncio.run(scan_trends("AI agents", SignalGraphConfig()))

    assert brief.theme == "AI agents"
    assert len(brief.signals) == 2
    assert len(brief.committed_signals) == 1
    assert brief.next_watch_candidates == ["example follow-up"]


def test_render_markdown_includes_signal() -> None:
    brief = make_brief()

    rendered = render_markdown(brief)

    assert "Example Signal" in rendered
    assert "https://example.com/signal" in rendered


def test_render_markdown_japanese_empty_sections() -> None:
    brief = make_brief(language="ja")
    brief.committed_signals = []
    brief.next_watch_candidates = []

    rendered = render_markdown(brief)

    assert "テーマ: AI agents" in rendered
    assert "## 正式追跡シグナル" in rendered
    assert "- None" in rendered

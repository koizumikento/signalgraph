from __future__ import annotations

import asyncio

from signalgraph.core import render_markdown, scan_trends
from signalgraph.models import (
    SignalDecision,
    SignalGraphConfig,
    TrackResearchResult,
    TrendBrief,
    TrendSignal,
)


def _signal(title: str, url: str, action: str = "commit") -> TrendSignal:
    return TrendSignal(
        title=title,
        source_type="oss",
        source_url=url,
        observed_at="2026-06-30",
        entities=["example"],
        summary="A concise signal.",
        why_it_matters="It indicates early overseas momentum.",
        japan_applicability="Could inform a Japan-facing product experiment.",
        novelty_score=0.9,
        momentum_score=0.8,
        credibility_score=0.8,
        decision=SignalDecision(action=action, reason="Strong signal.", confidence=0.8),
        next_watch_candidates=["example follow-up"],
    )


def test_scan_trends_uses_graph_and_deduplicates(monkeypatch) -> None:
    async def fake_research_tracks_with_codex(**kwargs):
        return [
            TrackResearchResult(
                track="oss",
                summary="OSS track",
                signals=[
                    _signal("A", "https://example.com/a"),
                    _signal("A duplicate", "https://example.com/a"),
                    _signal("B", "https://example.com/b", action="quarantine"),
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
    signal = _signal("A", "https://example.com/a")
    brief = TrendBrief(
        language="en",
        theme="AI agents",
        web_search="live",
        summary="Summary",
        signals=[signal],
        committed_signals=[signal],
        quarantined_signals=[],
        rejected_signals=[],
        next_watch_candidates=["example follow-up"],
    )

    rendered = render_markdown(brief)

    assert "A" in rendered
    assert "https://example.com/a" in rendered

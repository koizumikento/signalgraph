from __future__ import annotations

import asyncio

import pytest

from signalgraph.core import scan_trends
from signalgraph.graph import _brief_summary, _next_watch_candidates, _signal_score
from signalgraph.models import SignalGraphConfig, TrackResearchResult
from helpers import make_signal


def test_signal_score_weights_components() -> None:
    signal = make_signal(novelty=1.0, momentum=0.0, credibility=0.0)

    assert _signal_score(signal) == pytest.approx(0.35)


def test_next_watch_candidates_are_deduplicated_and_trimmed() -> None:
    signals = [
        make_signal(candidates=["Alpha", "alpha", "Beta"]),
        make_signal(url="https://example.com/other", candidates=["Gamma"]),
    ]

    assert _next_watch_candidates(signals) == ["Alpha", "Beta", "Gamma"]


def test_brief_summary_japanese() -> None:
    assert "正式追跡候補 1 件" in _brief_summary([make_signal()], [], [], "ja")


def test_empty_theme_is_rejected() -> None:
    with pytest.raises(ValueError, match="theme must not be empty"):
        asyncio.run(scan_trends(" ", SignalGraphConfig()))


def test_graph_classifies_commit_quarantine_and_reject(monkeypatch) -> None:
    commit = make_signal("Commit", "https://example.com/commit", action="commit")
    quarantine = make_signal(
        "Quarantine",
        "https://example.com/quarantine",
        action="quarantine",
        novelty=0.6,
        momentum=0.6,
        credibility=0.6,
    )
    reject = make_signal(
        "Reject",
        "https://example.com/reject",
        action="reject",
        novelty=0.1,
        momentum=0.1,
        credibility=0.1,
    )

    async def fake_research_tracks_with_codex(**kwargs):
        return [
            TrackResearchResult(
                track="oss",
                summary="OSS track",
                signals=[reject, quarantine, commit],
            )
        ]

    monkeypatch.setattr(
        "signalgraph.graph.research_tracks_with_codex",
        fake_research_tracks_with_codex,
    )

    brief = asyncio.run(scan_trends("AI agents", SignalGraphConfig()))

    assert [signal.title for signal in brief.committed_signals] == ["Commit"]
    assert [signal.title for signal in brief.quarantined_signals] == ["Quarantine"]
    assert [signal.title for signal in brief.rejected_signals] == ["Reject"]

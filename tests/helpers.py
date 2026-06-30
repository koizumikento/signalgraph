from __future__ import annotations

from signalgraph.models import SignalDecision, TrendBrief, TrendSignal


def make_signal(
    title: str = "Example Signal",
    url: str = "https://example.com/signal",
    action: str = "commit",
    novelty: float = 0.9,
    momentum: float = 0.8,
    credibility: float = 0.8,
    candidates: list[str] | None = None,
) -> TrendSignal:
    return TrendSignal(
        title=title,
        source_type="oss",
        source_url=url,
        observed_at="2026-06-30",
        entities=["example"],
        summary="A concise signal.",
        why_it_matters="It indicates early overseas momentum.",
        japan_applicability="Could inform a Japan-facing product experiment.",
        novelty_score=novelty,
        momentum_score=momentum,
        credibility_score=credibility,
        decision=SignalDecision(action=action, reason="Strong signal.", confidence=0.8),
        next_watch_candidates=candidates or ["example follow-up"],
    )


def make_brief(language: str = "en") -> TrendBrief:
    signal = make_signal()
    return TrendBrief(
        language=language,
        theme="AI agents",
        web_search="live",
        summary="Summary",
        signals=[signal],
        committed_signals=[signal],
        quarantined_signals=[],
        rejected_signals=[],
        next_watch_candidates=["example follow-up"],
    )

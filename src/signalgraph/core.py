from __future__ import annotations

from signalgraph.graph import run_signal_graph
from signalgraph.models import SignalGraphConfig, TrendBrief, TrendSignal


async def scan_trends(theme: str, config: SignalGraphConfig) -> TrendBrief:
    return await run_signal_graph(theme, config)


def render_markdown(brief: TrendBrief) -> str:
    if brief.language == "ja":
        return _render_markdown_ja(brief)
    return _render_markdown_en(brief)


def _render_markdown_en(brief: TrendBrief) -> str:
    lines = [
        "# SignalGraph Brief",
        "",
        f"Theme: {brief.theme}",
        f"Web search: {brief.web_search}",
        "",
        "## Summary",
        "",
        brief.summary,
        "",
        "## Committed Signals",
        "",
    ]
    lines.extend(_signal_lines(brief.committed_signals))
    lines.extend(["", "## Quarantine", ""])
    lines.extend(_signal_lines(brief.quarantined_signals))
    lines.extend(["", "## Rejected", ""])
    lines.extend(_signal_lines(brief.rejected_signals))
    lines.extend(["", "## Next Watch Candidates", ""])
    lines.extend(f"- {candidate}" for candidate in brief.next_watch_candidates)
    return "\n".join(lines).rstrip() + "\n"


def _render_markdown_ja(brief: TrendBrief) -> str:
    lines = [
        "# SignalGraph Brief",
        "",
        f"テーマ: {brief.theme}",
        f"Web検索: {brief.web_search}",
        "",
        "## サマリー",
        "",
        brief.summary,
        "",
        "## 正式追跡シグナル",
        "",
    ]
    lines.extend(_signal_lines(brief.committed_signals))
    lines.extend(["", "## 再検証", ""])
    lines.extend(_signal_lines(brief.quarantined_signals))
    lines.extend(["", "## 棄却", ""])
    lines.extend(_signal_lines(brief.rejected_signals))
    lines.extend(["", "## 次回の監視候補", ""])
    lines.extend(f"- {candidate}" for candidate in brief.next_watch_candidates)
    return "\n".join(lines).rstrip() + "\n"


def _signal_lines(signals: list[TrendSignal]) -> list[str]:
    if not signals:
        return ["- None"]
    lines: list[str] = []
    for signal in signals:
        score = (
            signal.novelty_score * 0.35
            + signal.momentum_score * 0.35
            + signal.credibility_score * 0.30
        )
        lines.extend(
            [
                f"### {signal.title}",
                "",
                f"- Source: {signal.source_url}",
                f"- Type: {signal.source_type}",
                f"- Score: {score:.2f}",
                f"- Decision: {signal.decision.action} ({signal.decision.confidence:.2f})",
                f"- Summary: {signal.summary}",
                f"- Why it matters: {signal.why_it_matters}",
                f"- Japan applicability: {signal.japan_applicability}",
                "",
            ]
        )
    return lines

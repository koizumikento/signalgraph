from __future__ import annotations

from dataclasses import dataclass, field

from pydantic_graph import BaseNode, End, GraphBuilder, GraphRunContext, StepContext

from signalgraph.codex_client import research_tracks_with_codex
from signalgraph.models import (
    ResearchTrack,
    SignalGraphConfig,
    TrackResearchResult,
    TrendBrief,
    TrendSignal,
)
from signalgraph.tracks import DEFAULT_TRACKS


@dataclass
class SignalGraphState:
    theme: str
    config: SignalGraphConfig
    tracks: tuple[ResearchTrack, ...] = DEFAULT_TRACKS
    track_results: list[TrackResearchResult] = field(default_factory=list)
    signals: list[TrendSignal] = field(default_factory=list)


@dataclass
class LoadResearchContract(BaseNode[SignalGraphState, None, TrendBrief]):
    async def run(self, ctx: GraphRunContext[SignalGraphState]) -> RunParallelResearch:
        if not ctx.state.theme.strip():
            raise ValueError("theme must not be empty")
        return RunParallelResearch()


@dataclass
class RunParallelResearch(BaseNode[SignalGraphState, None, TrendBrief]):
    async def run(self, ctx: GraphRunContext[SignalGraphState]) -> NormalizeSignals:
        ctx.state.track_results = await research_tracks_with_codex(
            theme=ctx.state.theme,
            language=ctx.state.config.language,
            web_search=ctx.state.config.web_search,
            tracks=ctx.state.tracks,
            repo=ctx.state.config.repo,
            max_parallel=ctx.state.config.max_parallel,
            codex_config_overrides=ctx.state.config.codex_config_overrides,
        )
        return NormalizeSignals()


@dataclass
class NormalizeSignals(BaseNode[SignalGraphState, None, TrendBrief]):
    async def run(self, ctx: GraphRunContext[SignalGraphState]) -> ScoreAndBrief:
        seen_urls: set[str] = set()
        signals: list[TrendSignal] = []
        for result in ctx.state.track_results:
            for signal in result.signals:
                normalized_url = str(signal.source_url).strip()
                if not normalized_url or normalized_url in seen_urls:
                    continue
                seen_urls.add(normalized_url)
                signals.append(signal)
        ctx.state.signals = signals
        return ScoreAndBrief()


@dataclass
class ScoreAndBrief(BaseNode[SignalGraphState, None, TrendBrief]):
    async def run(self, ctx: GraphRunContext[SignalGraphState]) -> End[TrendBrief]:
        signals = sorted(ctx.state.signals, key=_signal_score, reverse=True)[
            : ctx.state.config.max_signals
        ]

        committed = [
            signal
            for signal in signals
            if signal.decision.action == "commit"
            and _signal_score(signal) >= ctx.state.config.commit_threshold
        ]
        quarantined = [
            signal
            for signal in signals
            if signal not in committed
            and (
                signal.decision.action == "quarantine"
                or _signal_score(signal) >= ctx.state.config.quarantine_threshold
            )
        ]
        rejected = [
            signal for signal in signals if signal not in committed and signal not in quarantined
        ]

        return End(
            TrendBrief(
                theme=ctx.state.theme,
                language=ctx.state.config.language,
                web_search=ctx.state.config.web_search,
                summary=_brief_summary(committed, quarantined, rejected, ctx.state.config.language),
                signals=signals,
                committed_signals=committed,
                quarantined_signals=quarantined,
                rejected_signals=rejected,
                next_watch_candidates=_next_watch_candidates(signals),
            )
        )


def _signal_score(signal: TrendSignal) -> float:
    return (
        signal.novelty_score * 0.35 + signal.momentum_score * 0.35 + signal.credibility_score * 0.30
    )


def _brief_summary(
    committed: list[TrendSignal],
    quarantined: list[TrendSignal],
    rejected: list[TrendSignal],
    language: str,
) -> str:
    if language == "ja":
        return (
            f"正式追跡候補 {len(committed)} 件、再検証候補 {len(quarantined)} 件、"
            f"棄却 {len(rejected)} 件を検出しました。"
        )
    return (
        f"Found {len(committed)} committed signal(s), {len(quarantined)} quarantine "
        f"candidate(s), and {len(rejected)} rejected signal(s)."
    )


def _next_watch_candidates(signals: list[TrendSignal]) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for signal in signals:
        for candidate in signal.next_watch_candidates:
            key = candidate.strip()
            if key and key.lower() not in seen:
                seen.add(key.lower())
                candidates.append(key)
    return candidates[:20]


g = GraphBuilder(state_type=SignalGraphState, output_type=TrendBrief)


@g.step
async def start(ctx: StepContext[SignalGraphState, None, None]) -> LoadResearchContract:
    return LoadResearchContract()


g.add(
    g.node(LoadResearchContract),
    g.node(RunParallelResearch),
    g.node(NormalizeSignals),
    g.node(ScoreAndBrief),
    g.edge_from(g.start_node).to(start),
)

signal_graph = g.build()


async def run_signal_graph(theme: str, config: SignalGraphConfig) -> TrendBrief:
    state = SignalGraphState(theme=theme, config=config)
    return await signal_graph.run(state=state)

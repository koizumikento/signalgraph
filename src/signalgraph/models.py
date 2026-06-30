from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

OutputLanguage = Literal["en", "ja"]
WebSearchMode = Literal["disabled", "cached", "live"]
SignalSourceType = Literal["product", "oss", "paper", "news", "community", "funding"]
ResearchTrackName = Literal["products", "oss", "research", "community", "funding"]
SignalAction = Literal["commit", "quarantine", "reject"]


class ResearchTrack(BaseModel):
    name: ResearchTrackName
    prompt: str
    source_priorities: tuple[str, ...] = ()
    include_if: tuple[str, ...] = ()
    reject_if: tuple[str, ...] = ()
    scoring_notes: tuple[str, ...] = ()
    japan_translation: str
    max_findings: int = Field(default=5, ge=1, le=10)


class SignalDecision(BaseModel):
    action: SignalAction
    reason: str
    confidence: float = Field(ge=0, le=1)


class TrendSignal(BaseModel):
    title: str
    source_type: SignalSourceType
    source_url: str
    published_date: str | None = None
    observed_at: str
    entities: list[str] = Field(default_factory=list)
    summary: str
    why_it_matters: str
    japan_applicability: str
    novelty_score: float = Field(ge=0, le=1)
    momentum_score: float = Field(ge=0, le=1)
    credibility_score: float = Field(ge=0, le=1)
    decision: SignalDecision
    next_watch_candidates: list[str] = Field(default_factory=list)

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must be an absolute http or https URL")
        return value


class TrackResearchResult(BaseModel):
    track: ResearchTrackName
    summary: str
    signals: list[TrendSignal] = Field(default_factory=list)
    rejected_leads: list[str] = Field(default_factory=list)
    next_queries: list[str] = Field(default_factory=list)


class TrendBrief(BaseModel):
    theme: str
    language: OutputLanguage = "en"
    web_search: WebSearchMode = "live"
    summary: str
    signals: list[TrendSignal]
    committed_signals: list[TrendSignal]
    quarantined_signals: list[TrendSignal]
    rejected_signals: list[TrendSignal]
    next_watch_candidates: list[str]


class SignalGraphConfig(BaseModel):
    language: OutputLanguage = "en"
    web_search: WebSearchMode = "live"
    repo: str = "."
    max_parallel: int = 5
    max_signals: int = 20
    commit_threshold: float = 0.78
    quarantine_threshold: float = 0.55
    codex_config_overrides: tuple[str, ...] = ()

from __future__ import annotations

import asyncio
import sys
import types

from signalgraph.codex_client import (
    _build_prompt,
    _codex_output_schema,
    _effective_config_overrides,
    _format_track_contract,
    _language_name,
    _research_with_codex_client,
    research_tracks_with_codex,
)
from signalgraph.models import ResearchTrack, TrackResearchResult
from helpers import make_signal


TRACK = ResearchTrack(
    name="oss",
    prompt="Find OSS signals.",
    source_priorities=("GitHub repositories and releases.",),
    include_if=("The repository has recent meaningful activity.",),
    reject_if=("The repository is only a README concept.",),
    scoring_notes=("Raise credibility for primary repository evidence.",),
    japan_translation="Explain whether Japanese developer teams could use it.",
    max_findings=4,
)


class FakeSandbox:
    read_only = "read-only"


class FakeRunResult:
    def __init__(self, final_response: str) -> None:
        self.final_response = final_response


class FakeThread:
    def __init__(self, response: str) -> None:
        self.response = response
        self.runs: list[dict] = []

    async def run(self, prompt: str, output_schema: dict) -> FakeRunResult:
        self.runs.append({"prompt": prompt, "output_schema": output_schema})
        return FakeRunResult(self.response)


class FakeCodex:
    def __init__(self, response: str) -> None:
        self.response = response
        self.thread_starts: list[dict] = []
        self.thread = FakeThread(response)

    async def thread_start(self, **kwargs) -> FakeThread:
        self.thread_starts.append(kwargs)
        return self.thread


def test_build_prompt_includes_contract_and_language() -> None:
    prompt = _build_prompt("AI agents", "ja", "live", TRACK)

    assert "AI agents" in prompt
    assert "Japanese" in prompt
    assert "Track: oss" in prompt
    assert "Source priorities" in prompt
    assert "The repository has recent meaningful activity." in prompt
    assert "The repository is only a README concept." in prompt
    assert "Maximum findings" in prompt
    assert "Return only JSON" in prompt


def test_format_track_contract_includes_all_sections() -> None:
    contract = _format_track_contract(TRACK)

    assert "Mission" in contract
    assert "Source priorities" in contract
    assert "Include if" in contract
    assert "Reject if" in contract
    assert "Japan translation" in contract
    assert "- 4" in contract


def test_language_name() -> None:
    assert _language_name("ja") == "Japanese"
    assert _language_name("en") == "English"


def test_config_overrides_append_after_default() -> None:
    assert _effective_config_overrides(("foo=1",)) == (
        "stream_idle_timeout_ms=600000",
        "foo=1",
    )


def test_codex_output_schema_is_strict() -> None:
    schema = _codex_output_schema()

    assert schema["additionalProperties"] is False
    assert "track" in schema["required"]
    signal_schema = schema["$defs"]["TrendSignal"]
    assert signal_schema["properties"]["source_url"]["format"] in {"uri", "uri-reference"}


def test_research_with_codex_client_parses_json_and_uses_read_only_sandbox(tmp_path) -> None:
    result = TrackResearchResult(
        track="oss",
        summary="Found OSS signals.",
        signals=[make_signal()],
    )
    codex = FakeCodex(result.model_dump_json())

    parsed = asyncio.run(
        _research_with_codex_client(
            codex=codex,
            theme="AI agents",
            language="en",
            web_search="cached",
            track=TRACK,
            repo=str(tmp_path),
            sandbox_type=FakeSandbox,
        )
    )

    assert parsed.track == "oss"
    assert parsed.signals[0].title == "Example Signal"
    assert codex.thread_starts[0]["sandbox"] == "read-only"
    assert codex.thread_starts[0]["config"] == {"web_search": "cached"}
    assert codex.thread.runs[0]["output_schema"]["additionalProperties"] is False


def test_research_with_codex_client_falls_back_on_unstructured_response(tmp_path) -> None:
    codex = FakeCodex("not json")

    parsed = asyncio.run(
        _research_with_codex_client(
            codex=codex,
            theme="AI agents",
            language="en",
            web_search="live",
            track=TRACK,
            repo=str(tmp_path),
            sandbox_type=FakeSandbox,
        )
    )

    assert parsed.track == "oss"
    assert parsed.signals == []
    assert parsed.rejected_leads == ["not json"]


def test_research_tracks_with_codex_uses_sdk_session(monkeypatch, tmp_path) -> None:
    calls: dict[str, object] = {}

    class FakeCodexConfig:
        def __init__(self, config_overrides: tuple[str, ...]) -> None:
            self.config_overrides = config_overrides

    class FakeAsyncCodex:
        def __init__(self, config: FakeCodexConfig) -> None:
            calls["config"] = config

        async def __aenter__(self) -> FakeAsyncCodex:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            calls["closed"] = True

    fake_module = types.SimpleNamespace(AsyncCodex=FakeAsyncCodex, CodexConfig=FakeCodexConfig)
    monkeypatch.setitem(sys.modules, "openai_codex", fake_module)

    async def fake_research_with_codex_client(**kwargs):
        return TrackResearchResult(track=kwargs["track"].name, summary="ok")

    monkeypatch.setattr(
        "signalgraph.codex_client._research_with_codex_client",
        fake_research_with_codex_client,
    )

    results = asyncio.run(
        research_tracks_with_codex(
            theme="AI agents",
            language="en",
            web_search="live",
            tracks=(TRACK,),
            repo=str(tmp_path),
            max_parallel=1,
            codex_config_overrides=("foo=1",),
        )
    )

    assert results[0].track == "oss"
    assert calls["closed"] is True
    assert calls["config"].config_overrides == ("stream_idle_timeout_ms=600000", "foo=1")


def test_research_tracks_with_codex_reports_missing_dependency(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "openai_codex", None)

    try:
        asyncio.run(
            research_tracks_with_codex(
                theme="AI agents",
                language="en",
                web_search="live",
                tracks=(TRACK,),
                repo=".",
                max_parallel=1,
            )
        )
    except RuntimeError as exc:
        assert "openai-codex is required" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")

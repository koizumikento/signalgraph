# SignalGraph

SignalGraph is a small CLI and MCP tool for monitoring overseas trend signals
and translating them into Japan-facing business opportunities.

It is designed as a thin flow layer around Pydantic Graph and Codex SDK:

- run locally with `uvx`
- expose the same flow as an MCP tool
- use Pydantic models as the signal contract
- ask Codex SDK to research multiple tracks in parallel
- emit Markdown or JSON briefs

## Install

```bash
uvx signalgraph --help
```

During local development:

```bash
uv run signalgraph --help
```

Run validation, including the 80% coverage gate:

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
```

## Usage

Run a trend scan:

```bash
signalgraph scan "AI agent developer tools"
```

Write the brief to a file:

```bash
signalgraph scan "AI agent developer tools" --out weekly-brief.md
```

Use Japanese output:

```bash
signalgraph scan "AI agent developer tools" --language ja
```

Emit JSON:

```bash
signalgraph scan "AI agent developer tools" --format json
```

Control web search and parallelism:

```bash
signalgraph scan "healthcare AI" --web-search live --max-parallel 3
```

Pass Codex runtime config overrides:

```bash
signalgraph scan "AI agents" --codex-config stream_idle_timeout_ms=900000
```

SignalGraph passes a default 10 minute stream idle timeout override to Codex:

```bash
stream_idle_timeout_ms=600000
```

Run as an MCP server:

```bash
signalgraph-mcp
```

The MCP server exposes `scan_trends`.

## Research Tracks

The default scan runs five tracks:

- products: overseas launches, Product Hunt-style product signals, startup tools
- oss: GitHub/OSS projects, devtools, implementation momentum
- research: papers, technical breakthroughs, benchmark shifts
- community: Hacker News, Reddit, builder discussions, complaints
- funding: VC, accelerator, and startup financing signals

Each track returns structured `TrendSignal` records. The graph validates,
deduplicates, scores, and renders a concise brief.

Each track is defined as a research contract with source priorities, include
criteria, reject criteria, scoring notes, Japan-market translation guidance, and
candidate/finding limits. This keeps the parallel Codex research threads from
running as unconstrained search prompts while still forcing broader discovery.
By default, each track is instructed to inspect at least 15 plausible candidates
when web search is live, then return at most 8 final signals.

## Codex Authentication

SignalGraph uses the Codex SDK and therefore relies on the user's configured
Codex login or authentication. It does not manage API keys directly.

## Specification

See [docs/SPEC.md](docs/SPEC.md) for the initial design.

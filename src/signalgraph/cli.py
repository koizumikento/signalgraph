from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console

from signalgraph.core import render_markdown, scan_trends
from signalgraph.models import OutputLanguage, SignalGraphConfig, WebSearchMode

app = typer.Typer(help="Scan overseas trend signals with Codex-backed research tracks.")
console = Console()


@app.callback()
def main() -> None:
    """Scan overseas trend signals."""


@app.command()
def scan(
    theme: Annotated[str, typer.Argument(help="Research theme to monitor.")],
    language: Annotated[OutputLanguage, typer.Option("--language", "-l")] = "en",
    web_search: Annotated[WebSearchMode, typer.Option("--web-search")] = "live",
    out: Annotated[Path | None, typer.Option("--out", "-o")] = None,
    output_format: Annotated[Literal["markdown", "json"], typer.Option("--format")] = "markdown",
    repo: Annotated[Path, typer.Option("--repo")] = Path("."),
    max_parallel: Annotated[int, typer.Option("--max-parallel")] = 5,
    max_signals: Annotated[int, typer.Option("--max-signals")] = 20,
    codex_config: Annotated[
        list[str] | None,
        typer.Option(
            "--codex-config",
            help="Codex runtime override in TOML key=value form. Can be passed multiple times.",
        ),
    ] = None,
) -> None:
    """Run a trend scan and print a brief."""
    config = SignalGraphConfig(
        language=language,
        web_search=web_search,
        repo=str(repo),
        max_parallel=max_parallel,
        max_signals=max_signals,
        codex_config_overrides=tuple(codex_config or ()),
    )
    try:
        brief = asyncio.run(scan_trends(theme, config))
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="theme") from exc

    rendered = brief.model_dump_json(indent=2) if output_format == "json" else render_markdown(brief)

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
    elif output_format == "json":
        console.out(rendered)
    else:
        console.print(rendered, markup=False)

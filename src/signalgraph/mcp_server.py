from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from signalgraph.core import scan_trends
from signalgraph.models import OutputLanguage, SignalGraphConfig, WebSearchMode

mcp = FastMCP("signalgraph")


@mcp.tool()
async def scan_trends_tool(
    theme: str,
    language: OutputLanguage = "en",
    web_search: WebSearchMode = "live",
    repo: str = ".",
    max_parallel: int = 5,
    max_signals: int = 20,
    codex_config_overrides: list[str] | None = None,
) -> dict:
    """Scan overseas trend signals for a theme."""
    brief = await scan_trends(
        theme,
        SignalGraphConfig(
            language=language,
            web_search=web_search,
            repo=repo,
            max_parallel=max_parallel,
            max_signals=max_signals,
            codex_config_overrides=tuple(codex_config_overrides or ()),
        ),
    )
    return brief.model_dump()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

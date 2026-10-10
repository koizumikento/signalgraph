"""Private, bounded Streamable HTTP adapter for the existing research graph."""

from __future__ import annotations

import asyncio
import hmac
import inspect
import json
import os
from pathlib import Path
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.requests import Request
from starlette.responses import Response

from signalgraph.core import scan_trends
from signalgraph.models import OutputLanguage, SignalGraphConfig, WebSearchMode
from signalgraph.sites_protocol import modern_response

MAX_BODY = 16_384
SCAN_TIMEOUT = 900
# Disable local execution and connected tools, retaining Codex's web research.
RESEARCH_ONLY_OVERRIDES = (
    'approval_policy="never"',
    "mcp_servers={}",
    *(
        f"features.{name}=false"
        for name in (
            "shell_tool",
            "unified_exec",
            "apps",
            "plugins",
            "remote_plugin",
            "multi_agent",
            "multi_agent_v2",
            "code_mode",
            "code_mode_host",
            "computer_use",
            "browser_use",
            "browser_use_external",
            "browser_use_full_cdp_access",
            "in_app_browser",
            "image_generation",
            "hooks",
            "memories",
            "workspace_dependencies",
            "skill_mcp_dependency_install",
        )
    ),
)


def create_app(token: str, repo: Path):
    """Bind one service credential and one operator-selected empty working directory."""
    if len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
        raise ValueError("backend token must contain at least 32 non-whitespace ASCII characters")
    repo = repo.resolve(strict=True)
    if not repo.is_dir() or any(repo.iterdir()):
        raise ValueError("research directory must be an existing empty directory")

    server = FastMCP(
        "signalgraph",
        stateless_http=True,
        json_response=False,
        # A tunnel sets this exact Host; requests with Origin are refused below.
        transport_security=TransportSecuritySettings(
            allowed_hosts=["127.0.0.1:8000"],
            allowed_origins=[],
        ),
    )
    busy = asyncio.Lock()

    @server.tool(
        name="scan_trends_tool",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def hosted_scan(
        theme: Annotated[str, Field(min_length=1, max_length=2000)],
        language: OutputLanguage = "en",
        web_search: WebSearchMode = "live",
        repo: Literal["."] = ".",
        max_parallel: Annotated[int, Field(ge=1, le=5, strict=True)] = 5,
        max_signals: Annotated[int, Field(ge=1, le=40, strict=True)] = 20,
        codex_config_overrides: Annotated[list[str] | None, Field(max_length=0)] = None,
    ) -> dict:
        """Scan overseas trends. Hosted mode requires repo='.' and no runtime overrides.

        theme: 1-2000 characters; max_parallel: 1-5; max_signals: 1-40.
        Uses five fixed tracks, existing scoring thresholds, and source URLs.
        """
        if not theme.strip():
            raise ValueError("theme must contain 1-2000 characters")
        if busy.locked():
            raise ValueError("research is busy; wait for the current scan before retrying")
        async with busy:
            try:
                async with asyncio.timeout(SCAN_TIMEOUT):
                    brief = await scan_trends(
                        theme,
                        SignalGraphConfig(
                            language=language,
                            web_search=web_search,
                            repo=str(research_repo),
                            max_parallel=max_parallel,
                            max_signals=max_signals,
                            codex_config_overrides=RESEARCH_ONLY_OVERRIDES,
                        ),
                    )
                return brief.model_dump()
            except TimeoutError:
                raise ValueError(
                    "research timed out; use a narrower theme before retrying"
                ) from None
            except Exception:
                # Upstream exceptions may contain credentials, prompts, or local paths.
                raise ValueError(
                    "research unavailable; ask the operator to check the backend"
                ) from None

    research_repo = repo
    app = server.streamable_http_app()

    async def protected(scope, receive, send):
        if scope["type"] != "http":
            return await app(scope, receive, send)
        request = Request(scope, receive)
        if not hmac.compare_digest(
            request.headers.get("authorization", "").encode(),
            f"Bearer {token}".encode(),
        ):
            return await Response(status_code=401)(scope, receive, send)
        if "origin" in request.headers:
            return await Response(status_code=403)(scope, receive, send)
        if request.headers.get("host") != "127.0.0.1:8000":
            return await Response(status_code=421)(scope, receive, send)
        if request.url.path != "/mcp":
            return await Response(status_code=404)(scope, receive, send)
        if request.method != "POST":
            return await Response(status_code=405, headers={"Allow": "POST"})(scope, receive, send)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_BODY:
                return await Response(status_code=413)(scope, receive, send)
        try:
            message = json.loads(body)
            allowed = inspect.signature(hosted_scan).parameters.keys()
            response = await modern_response(message, request, server, allowed)
            if response is not None:
                return await response(scope, receive, send)
            if isinstance(message, dict) and message.get("method") == "tools/call":
                arguments = message.get("params", {}).get("arguments", {})
                if not isinstance(arguments, dict) or arguments.keys() - allowed:
                    return await Response(status_code=400)(scope, receive, send)
        except (ValueError, AttributeError):
            return await Response(status_code=400)(scope, receive, send)

        # Subsequent receive calls must observe disconnects, not replay the body again.
        delivered = False

        async def receive_once():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        return await app(scope, receive_once, send)

    return protected


def main() -> None:
    import uvicorn

    # Do not let the Codex child process inherit the backend service credential.
    token = os.environ.pop("SIGNALGRAPH_BACKEND_TOKEN", "")
    repo = Path(os.environ.pop("SIGNALGRAPH_RESEARCH_DIR"))
    uvicorn.run(create_app(token, repo), host="127.0.0.1", port=8000, access_log=False)


if __name__ == "__main__":
    main()

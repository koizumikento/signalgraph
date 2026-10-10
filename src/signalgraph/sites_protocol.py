"""Modern HTTP binding for the Site's single tool, sharing FastMCP execution."""

from __future__ import annotations

import base64
import json

from jsonschema import ValidationError as SchemaError
from jsonschema import validate
from mcp import types
from mcp.server.fastmcp.exceptions import ToolError
from mcp.shared.version import SUPPORTED_PROTOCOL_VERSIONS
from pydantic import ValidationError
from sse_starlette import EventSourceResponse
from starlette.requests import Request
from starlette.responses import JSONResponse

from signalgraph import __version__

MODERN_VERSION = "2026-07-28"
META_PREFIX = "io.modelcontextprotocol/"
VERSIONS = [MODERN_VERSION, *reversed(SUPPORTED_PROTOCOL_VERSIONS)]
RESULT_META = {META_PREFIX + "serverInfo": {"name": "signalgraph", "version": __version__}}
CACHE = {"ttlMs": 0, "cacheScope": "private"}


async def modern_response(message, request: Request, server, allowed_arguments):
    """Return None for legacy traffic, leaving its SDK transport unchanged."""
    envelope = message if isinstance(message, dict) else {}
    method = envelope.get("method")
    params = envelope.get("params", {})
    meta = params.get("_meta", {}) if isinstance(params, dict) else {}
    header_version = request.headers.get("mcp-protocol-version")
    body_version = meta.get(META_PREFIX + "protocolVersion") if isinstance(meta, dict) else None
    modern = header_version == MODERN_VERSION or body_version == MODERN_VERSION
    modern |= header_version is not None and header_version not in SUPPORTED_PROTOCOL_VERSIONS
    modern |= body_version is not None and body_version not in SUPPORTED_PROTOCOL_VERSIONS
    if method != "server/discover" and not modern:
        return None

    request_id = envelope.get("id")
    if not isinstance(request_id, (int, str)) or isinstance(request_id, bool):
        request_id = None

    def error(code, text, status=400, data=None):
        detail = {"code": code, "message": text}
        if data is not None:
            detail["data"] = data
        return JSONResponse(
            {"jsonrpc": "2.0", "id": request_id, "error": detail}, status_code=status
        )

    def result(value):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                **value,
                "resultType": "complete",
                "_meta": RESULT_META,
            },
        }

    try:
        types.JSONRPCRequest.model_validate(message)
    except ValidationError:
        return error(-32600, "Invalid JSON-RPC request")
    if not isinstance(params, dict):
        return error(-32602, "params must be an object")
    if (
        request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        != "application/json"
    ):
        return error(-32600, "Content-Type must be application/json", 415)
    accept = {
        item.split(";", 1)[0].strip().lower()
        for item in request.headers.get("accept", "").split(",")
    }
    if not {"application/json", "text/event-stream"} <= accept:
        return error(-32600, "Accept must include application/json and text/event-stream", 406)

    # Sites also probes discovery before choosing a version, with exactly params={}.
    bootstrap = method == "server/discover" and envelope.get("params") == {}
    if any(
        ord(char) < 32 or ord(char) > 126
        for field in (
            "mcp-protocol-version",
            "mcp-method",
            "mcp-name",
        )
        for char in request.headers.get(field, "")
    ):
        return error(-32020, "Invalid character in metadata header")
    if not bootstrap:
        if not isinstance(meta, dict) or not isinstance(body_version, str):
            return error(-32602, "_meta must declare protocolVersion and clientCapabilities")
        if header_version != body_version or request.headers.get("mcp-method") != method:
            return error(-32020, "Protocol version or method header does not match the body")
        if not isinstance(meta.get(META_PREFIX + "clientCapabilities"), dict):
            return error(-32602, "_meta.clientCapabilities must be an object")
        try:
            types.ClientCapabilities.model_validate(meta[META_PREFIX + "clientCapabilities"])
            if META_PREFIX + "clientInfo" in meta:
                types.Implementation.model_validate(meta[META_PREFIX + "clientInfo"])
        except ValidationError:
            return error(-32602, "Invalid client capabilities or clientInfo")
    elif request.headers.get("mcp-method", method) != method:
        return error(-32020, "Method header does not match the body")
    requested = header_version if header_version is not None else body_version
    if requested is not None and requested not in VERSIONS:
        return error(
            -32022,
            "Unsupported protocol version",
            data={"supported": VERSIONS, "requested": requested},
        )

    if method in {"tools/call", "resources/read", "prompts/get"}:
        name = request.headers.get("mcp-name", "")
        if name.startswith("=?base64?") and name.endswith("?="):
            try:
                name = base64.b64decode(name[9:-2], validate=True).decode("utf-8")
            except (ValueError, UnicodeError):
                return error(-32020, "Invalid encoded Mcp-Name")
        field = "uri" if method == "resources/read" else "name"
        if not name or name != params.get(field):
            return error(-32020, "Mcp-Name does not match the body")

    if method == "server/discover":
        if params.keys() - {"_meta"}:
            return error(-32602, "Discovery accepts only _meta")
        return JSONResponse(
            result({"supportedVersions": VERSIONS, "capabilities": {"tools": {}}, **CACHE}),
            headers={"Cache-Control": "no-store"},
        )
    if method == "ping":
        if params.keys() - {"_meta"}:
            return error(-32602, "Ping accepts only _meta")
        return JSONResponse(result({}))
    tools = await server.list_tools()
    if method == "tools/list":
        if params.keys() - {"_meta", "cursor"} or params.get("cursor") is not None:
            return error(-32602, "Invalid cursor; this tool list has a single page")
        return JSONResponse(
            result(
                {
                    "tools": [
                        tool.model_dump(mode="json", by_alias=True, exclude_none=True)
                        for tool in tools
                    ],
                    **CACHE,
                }
            ),
            headers={"Cache-Control": "no-store"},
        )
    if method != "tools/call":
        return error(-32601, "Method not found", 404)

    if params.keys() - {"_meta", "name", "arguments"}:
        return error(-32602, "Unsupported tool call parameters")
    tool = next((tool for tool in tools if tool.name == name), None)
    arguments = params.get("arguments", {})
    if tool is None or not isinstance(arguments, dict) or arguments.keys() - allowed_arguments:
        return error(-32602, "Unknown tool or invalid arguments")
    try:
        validate(arguments, tool.inputSchema)
    except SchemaError:
        return error(-32602, "Arguments do not match the discovered inputSchema")

    async def stream():
        try:
            content = await server.call_tool(name, arguments)
            value = {
                "content": [
                    item.model_dump(mode="json", by_alias=True, exclude_none=True)
                    for item in content
                ],
                "isError": False,
            }
        except ToolError as exc:
            # The registered hosted tool already redacts research exceptions.
            value = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
        yield {"event": "message", "data": json.dumps(result(value))}

    # Establish headers immediately; keepalives and disconnect cancellation are native.
    return EventSourceResponse(stream())

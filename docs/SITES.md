# Sites MCP deployment

SignalGraph needs a **separate Python backend**. Sites runs a Cloudflare Worker;
it cannot launch the Codex executable, Pydantic Graph, or access the operator's
local Codex login. The deployable Site source is `sites/`, a dependency-free
Worker ESM project following the official Sites Worker starter artifact layout.
No Site, tunnel, OAuth registration, or cloud resources are created by these files.

## Ownership and authority

The Worker accepts stateless `POST /mcp` and forwards only to an operator-configured
HTTPS `/mcp` URL. Python's existing MCP SDK handles initialization, discovery,
notifications, protocol version negotiation, calls, and JSON-RPC errors. GET and
DELETE return 405: there are no sessions, background subscriptions, or replay.
SSE POST responses and SDK keepalives stream without buffering, allowing long
research calls through an HTTP tunnel. The backend runs at most one scan at a
time, with a 15-minute deadline; callers must allow that duration. Disconnects
are not evidence of cancellation or completion. Do not automatically replay a
lost call: it can consume another Codex research run.

Sites owns OAuth and supplies trusted `oai-authenticated-user-id`. Every MCP
request requires identity equal to the Site-scoped `SIGNALGRAPH_ALLOWED_USER_ID`.
Missing identity returns 401; a different or unconfigured member returns 403.
Discovery contains no private data but uses the same gate. Configure the allowed
ID from trusted Site identity, never from a user-supplied tool argument or email.
An `OAI-Sites-Authorization` service bypass token supplies **no user identity**
and therefore cannot authorize a research call. Do not expose this Worker through
a standalone host that permits callers to forge the Sites identity header.

The backend authenticates a separate service token, including discovery; it does
not consume user identity headers or pretend the service token is a Codex login.
Run one backend for one operator-owned Codex account and one allowed Site user.
Sites visitors do not lend their own Codex credentials. Use a dedicated VM/container
with no unrelated private files, connectors, plugins, or services; an ordinary
shared desktop account is unsuitable.
Authenticate Codex normally on that backend account; never copy an existing
auth file into Sites, the repository, or a deployment artifact. Read-only
sandboxing is retained. Fixed backend config disables shell/unified execution,
connected apps/MCP/plugins, agent delegation, code mode,
computer/browser control, hooks, memories, and dependency tools. The service
token and research directory are removed from the backend environment before
Codex is launched. Runtime config feature behavior must be reevaluated when
upgrading the pinned Codex runtime; unit tests do not prove live tool isolation.
The pinned runtime has no `view_image` disable feature: its built-in image reader
can access readable files. VM/container filesystem isolation is therefore a required
deployment boundary, not a claim that read-only sandboxing prevents private reads.

Worker and backend reject bodies over 16 KiB. The Worker validates same-origin
Origin headers and strips identity, cookies, caller authorization, session IDs,
and unrelated headers when forwarding. It never follows redirects. Backend
Origin headers are refused; its Host must be `127.0.0.1:8000`. Upstream research
exceptions are replaced with a generic actionable `isError` tool result; Worker
network/server failures return a redacted 502. Access logging is disabled; do not
enable request-body, authorization-header, or prompt logging in an ingress.

## Contract compatibility

The actual existing tool name is `scan_trends_tool` (the older README called it
`scan_trends`). Hosted discovery keeps all seven input field names and defaults:

| Field | Hosted constraint |
| --- | --- |
| `theme` | Nonblank, 1-2000 characters |
| `language` | `en` or `ja` |
| `web_search` | `disabled`, `cached`, or `live` |
| `repo` | Only `.`; mapped to the operator's empty research directory |
| `max_parallel` | Integer 1-5 |
| `max_signals` | Integer 1-40 |
| `codex_config_overrides` | Only omitted, null, or an empty list |

Unknown input keys are rejected. The stricter hosted limits are intentional:
remote callers cannot select PC paths, shell commands, or runtime overrides.
The Python library, CLI, and original stdio server retain their local behavior.
The existing five research tracks, scoring thresholds (0.78 / 0.55), source URL
validation, deduplication, signal categories, and follow-up candidate cap are
shared through `core.scan_trends` and `graph.py`. There is no recursive expansion.
The minimum 15 candidates and maximum 8 findings per track are existing prompt
instructions, not proof that the model searched that many sources. Hosted mode
also bounds returned total signals; it introduces no replacement research flow.
Results retain the existing `TrendBrief` JSON text content. The current `dict`
return type advertises no `outputSchema`/`structuredContent`; this adapter does
not silently replace that contract. This single tool has no pagination. There
is no historical storage or new download/path tool; CLI file output stays local.

## Prepare the private backend

Use Python 3.11-3.13 and the repository lockfile:

```sh
uv sync --locked --extra sites
uv run --locked --extra sites signalgraph-sites-backend
```

Before starting, supply the following using your service manager's secret store
or private process environment (names only are listed in `sites/.env.example`):

| Runtime | Name | Meaning |
| --- | --- | --- |
| Backend and Site | `SIGNALGRAPH_BACKEND_TOKEN` | Same random, at least 32-character ASCII service credential |
| Backend | `SIGNALGRAPH_RESEARCH_DIR` | Existing, empty, dedicated operator directory |
| Site | `SIGNALGRAPH_BACKEND_URL` | Fixed HTTPS URL ending exactly in `/mcp` |
| Site | `SIGNALGRAPH_ALLOWED_USER_ID` | One trusted Site-scoped user ID |

The backend binds only to `127.0.0.1:8000`. For a private machine, an existing
named **Cloudflare Tunnel** can publish a dedicated HTTPS hostname to that
loopback HTTP service; set its origin `httpHostHeader` to `127.0.0.1:8000`, retain
chunked encoding, and disable proxy buffering. Its published application is
Internet-routable but every route is protected by the backend token. Use an
exact `/mcp` ingress path and a final `http_status:404` fallback. Configure and
run the named tunnel using Cloudflare's supported dashboard/service workflow;
do not use a temporary Quick Tunnel for production. The existing account,
domain, tunnel credentials and persistent backend host are operator prerequisites,
not created by this PR. A managed HTTPS reverse proxy with the same Host override
and streaming behavior is an alternative. Do not expose port 8000 to a network
or add a browser redirect login page to the backend endpoint. Additional Access
policies require a separately verified service-auth route.

## Build, package, and deploy the Site source

Local checks have no Node dependencies or npm install step:

```sh
mkdir -p work
uv run --locked --extra dev --extra sites pytest --basetemp=work/pytest
uv run --locked --extra dev --extra sites ruff check .
uv run --locked --extra dev --extra sites ruff format --check .
cd sites
npm test
npm run build
npm run validate
```

Build output is `sites/dist/server/index.js` (default ESM `fetch`) plus
`sites/dist/.openai/hosting.json`. The source manifest declares `mcp`, leaves
unused D1/R2 null, and contains no secrets or invented Site ID.

When deployment is separately authorized, select `sites/` as the source checkout
and use the installed official Sites skill's Worker ESM/local-only preparation
workflow. For a new Site, register it owner-private, then persist the returned
ID using `set-project-id.mjs`; for an existing Site, open its retained source
and preserve its ID/audience. Configure only the three Site runtime values above
through native Sites secret tools. Never put secret values in the manifest,
build artifacts, credentials files, browser code, or a prompt.

Use Sites' source workflow helper with its returned write credential over stdin;
package with ordered commands `["npm","test"]`, `["npm","run","build"]`,
`["npm","run","validate"]` and an absolute archive path. Save and deploy with
the official owner-private workflow. Do not deploy with raw Wrangler, add a
second OAuth implementation, or register a replacement plugin. After deployment,
verify `get_site(include_mcp_connection: true)` reports MCP enabled and reuse the
returned platform plugin. An authorized signed-in client must initialize,
discover `scan_trends_tool`, and complete a read-only call; an anonymous client,
a wrong member and service bypass alone must fail. Verify backend SSE keepalives
and client timeout with an actual long call before operational acceptance.

## Validation and cleanup boundaries

`tests/test_sites_backend.py` uses isolated temporary directories and the real
SDK HTTP adapter with mocked research. It compares local/hosted graph output,
source provenance, discovery, notification responses, authorization, forbidden
inputs, size/protocol errors, and redacted failure/timeout results.
`sites/tests/worker.test.mjs` verifies identity gates, fixed forwarding, secret
header filtering, redirect rejection and unbuffered SSE using synthetic fixtures.
CI runs Python tests/coverage, Ruff and the Worker tests/build/artifact check.
These establish local/mock contracts; they do not establish live Codex login,
live model tool isolation, hosted Sites identity, tunnel connectivity, plugin
installation, or client acceptance. No live external research is required for
tests. Do not describe those boundaries as passed without separate evidence.

Record any test server PID and exact temporary resource paths/IDs before using
them. Stop only owned test processes and remove only generated fixture directories,
`sites/dist`, Python test caches and the worktree's disposable `.venv` after
validation. Preserve shared caches, source, lockfiles, reproducible tests, and
the PR worktree/branch. If isolated hosted tests are later authorized, remove
only their newly created Site/tunnel/plugin/storage resources after testing and
record the verified deletion status. Never rewrite existing hosted data to test.

## Official references checked 2026-10-10

- [MCP 2025-11-25 Streamable HTTP](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [Official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk): implementation uses locked v1.28.1,
  stateless HTTP and POST SSE; later SDK/protocol revisions require compatibility checks.
- [Codex 0.144.4 config schema](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/config.schema.json)
  and offline `codex features list` from the SDK's pinned runtime.
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/)
- [Tunnel origin parameters](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/origin-parameters/)
- Installed official Sites v1.0.0 skill: `site-mcp-server.md`,
  `identity-and-secrets.md`, `storage.md`, and `templates/worker-esm-starter/`.

# Agent Notes

This repository is a small Python package for Codex-backed overseas trend
research. Keep the architecture narrow:

- `src/signalgraph/graph.py` owns the Pydantic Graph flow.
- `src/signalgraph/codex_client.py` owns Codex SDK integration.
- `src/signalgraph/models.py` owns public data contracts.
- `src/signalgraph/cli.py` and `src/signalgraph/mcp_server.py` should stay thin.

## Codex SDK Rules

- Use the user's configured Codex authentication. Do not read, print, or inspect
  local Codex auth files, access tokens, or secrets.
- Start Codex threads with read-only sandboxing unless a future feature clearly
  needs writes.
- Pass runtime overrides through `codex_config_overrides` using the same
  `key=value` TOML syntax as `codex --config`.
- Keep web access explicit through `web_search` config.

## Research Rules

- Favor structured signal records over free-form summaries.
- Every committed signal should have a source URL and a reason it matters.
- Keep autonomous recursion bounded with depth, maximum new candidates, and
  scoring thresholds.
- Tests should mock Codex SDK calls; live Codex authentication is not required
  for unit tests.

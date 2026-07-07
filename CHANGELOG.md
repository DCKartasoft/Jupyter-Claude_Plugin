# Changelog

<!-- <START NEW CHANGELOG ENTRY> -->

## Unreleased

- Frontend cell-write path: Claude calls `mcp__jupyter__*` tools (insert_cell, insert_execute_code_cell) directly; frontend does not parse code blocks. Cleaner separation of concerns.
- React 18 pinned to `^18.2.0` for JupyterLab 4 type compatibility; `tsconfig.json` moduleResolution set to `bundler`.
- Frontend built: React chat panel with message list, WebSocket client with auto-reconnect, four v1 commands (chat, generate, explain, fix), cell toolbar buttons and context menu entries.
- Server extension built: `ClaudeExtensionApp` with configurable backend/model/region traits, `ClaudeSDKClient` per WS connection, chat handler at `/jupyter-claude/chat`.
- JupyterLab extension scaffold generated via copier (frontend-and-server, package `@dckartasoft/jupyter-claude`, Python `jupyter_claude`).
- Fixed malformed `labextension_name` (`myextension@dc-ks/jupyter-claude` → `@dckartasoft/jupyter-claude`) across `package.json`, `pyproject.toml`, `schema/plugin.json`, `.copier-answers.yml`, `ui-tests/package.json`.
- Root `CHANGELOG.md` is now the single changelog; `docs/CHANGELOG.md` removed.
- Initial commit landed (root `6e4db50`): plan, decisions, doc-keeper cron config, uv boilerplate, stub.
- Haiku doc-keeper cron: every 10 minutes reads `docs/DECISIONS.md` and syncs `PLAN.md`, `README.md`, `CHANGELOG.md`, `Architecture.md`.
- Corrected MCP server registration: `fetch` and `git` are Python packages; use `uvx` not `npx`.
- Plan location: dual (`~/.claude/plans/...` internal + `docs/PLAN.md` versioned).
- Dev environment locked to Homebrew + `uv` (no pipx); `uvx` replaces pipx for one-shot tools.
- Global MCP servers registered at user scope: filesystem, memory, sequential-thinking, fetch (Python), git (Python), jupyter (HTTP).
- Support both Anthropic direct and AWS Bedrock backends; env-var driven, inference-profile model IDs for Bedrock.
- MCP on both sides: plugin backend acts as MCP client; connects to `jupyter-mcp-server` for cell R/W/execute. No hand-rolled cell tools.
- Target: JupyterLab frontend-and-server extension (not classic + magics); richest UX with sidebar chat, cell toolbar, context menus.
- Four v1 interactions: chat about notebook, generate cell, explain/document cell, fix last error.
- Project initialized (2026-07-07).

_This changelog is maintained by an automated doc-keeper — it re-writes from [docs/DECISIONS.md](docs/DECISIONS.md) every 10 minutes._

<!-- <END NEW CHANGELOG ENTRY> -->

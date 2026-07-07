# Changelog

<!-- <START NEW CHANGELOG ENTRY> -->

## Unreleased

- MCP server enumeration + runtime selector: `jupyter_claude/mcp_discovery.py` reads `~/.claude.json`, new `enabled_mcp_servers` trait with GET/POST REST endpoints at `/jupyter-claude/mcp-servers`, frontend dialog to enable/disable individual servers (default: `["jupyter"]`), MCP client restarts with fresh filter on selection change.
- `main_model_tier` trait for speed/quality tradeoff: Sonnet 4.6 is default; Opus for max quality, Haiku for max speed; resolved model sent back in `ready` frame.
- Custom `claudeIcon` (blue SVG spark): new `src/icons.ts` exports an inline LabIcon showing a stylised blue 4-point spark (`#4361ee`), replacing generic `codeIcon` on sidebar tab and Open Chat button.
- Full command set on notebook toolbar: all four Claude commands (Open Chat, Generate, Explain, Fix) now appear as icon-only toolbar buttons (ranks 60–63) with tooltips; cell toolbar keeps just Explain.
- Runtime model selector in chat panel: dropdown to switch tier (opus/sonnet/haiku) per conversation without editing config; disabled for Anthropic direct or during requests; tier selection resets conversation history.
- Panel spinner and command-triggered busy state: animated "Claude is thinking…" indicator while processing; command flows now set busy state alongside panel updates.
- Cell-type dropdown for Generate command: select code/markdown/raw before description; prompts adapt by type and respect no-execute for markdown/raw cells.
- Command dialogs use JupyterLab InputDialog instead of `window.prompt()` (browser-blocked); fixed last-error tracking by notebook ID consistency.
- `page_config.json` cleaned: removed stale disabled/locked extension entries that silently blocked activation.
- Labextension linked as symlink via `jupyter labextension develop . --overwrite` in dev workflow; clears stale bundled copies.
- Bedrock config expanded: added `aws_profile` trait for shared AWS SSO, plus `default_opus_model`, `default_sonnet_model`, `default_haiku_model` traits for per-tier inference-profile IDs (defaults: `us.anthropic.claude-opus-4-7`, `us.anthropic.claude-sonnet-4-6`, `us.anthropic.claude-haiku-4-5-20251001-v1:0`).
- `main_model_tier` trait for speed/quality tradeoff: Sonnet 4.6 is default; Opus for max quality, Haiku for max speed.
- Frontend cell-write path: Claude calls `mcp__jupyter__*` tools (insert_cell, insert_execute_code_cell) directly; frontend does not parse code blocks. Cleaner separation of concerns.
- React 18 pinned to `^18.2.0` for JupyterLab 4 type compatibility; `tsconfig.json` moduleResolution set to `bundler`.
- Frontend built: React chat panel with message list, WebSocket client with auto-reconnect, four v1 commands (chat, generate, explain, fix), cell toolbar buttons and context menu entries.
- Server extension built: `ClaudeExtensionApp` with configurable backend/model/region traits, `ClaudeSDKClient` per WS connection, chat handler at `/jupyter-claude/chat`.
- JupyterLab extension scaffold generated via copier (frontend-and-server, package `@dckartasoft/jupyter-claude`, Python `jupyter_claude`).
- Fixed malformed `labextension_name` (`myextension@dc-ks/jupyter-claude` → `@dckartasoft/jupyter-claude`) across all config and code files.
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

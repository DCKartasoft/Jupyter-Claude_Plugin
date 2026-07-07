# Decisions Journal

Append-only log of development decisions. The Haiku doc-keeper (see `.claude/scheduled_tasks.json`) reads this file every 10 minutes and updates `PLAN.md`, `README.md`, `CHANGELOG.md`, and `Architecture.md` to stay in sync.

**Format for new entries:**

```
## [YYYY-MM-DD HH:MM] Short title
Category: {scope|architecture|tooling|dependency|process}
Description of what was decided.
Rationale: why this choice over alternatives.
```

Newest entries at the bottom.

---

## [2026-07-07 10:57] Project initialized
Category: scope
Empty working directory `/Users/DC-KS/Dev/Jupyter-Claude_Plugin` with a stub `Jupyter-Claude-Plug.py`. Goal: JupyterLab extension enabling Claude to collaborate on notebook code and documentation.
Rationale: fresh greenfield project — no existing code to preserve.

## [2026-07-07 11:00] Target: JupyterLab extension (not classic + magics)
Category: scope
Build a JupyterLab frontend-and-server extension, not an IPython cell-magic plugin or a pure-ipywidgets UI.
Rationale: richest UX (sidebar chat, cell toolbar buttons, context menus). User confirmed via question.

## [2026-07-07 11:00] Backend: Claude Agent SDK (Python)
Category: architecture
Use `claude-agent-sdk` (Python) as the backend, not the bare `anthropic` SDK.
Rationale: gives us the agent loop, tool-use plumbing, and MCP client for free. User confirmed.

## [2026-07-07 11:00] v1 features
Category: scope
Four v1 interactions: chat about the notebook, generate a new cell from a prompt, explain/document an existing cell, fix the last cell error.
Rationale: user selected all four in the requirements question.

## [2026-07-07 11:03] Support both Anthropic direct and AWS Bedrock backends
Category: architecture
Must work with either Anthropic API (`ANTHROPIC_API_KEY`) or AWS Bedrock (`CLAUDE_CODE_USE_BEDROCK=1` + AWS creds).
Rationale: user constraint — some environments will only have Bedrock access. SDK selects via env vars, not constructor args. Bedrock model IDs must use inference-profile format (e.g. `us.anthropic.claude-opus-4-8`).

## [2026-07-07 11:07] Use MCP servers on both sides
Category: architecture
Plugin backend acts as an MCP client (via Agent SDK) and connects to `jupyter-mcp-server` (Datalayer) for cell R/W/execute. No hand-rolled cell tools.
Rationale: user request. jupyter-mcp-server exposes `read_cell`, `insert_cell`, `overwrite_cell_source`, `execute_cell`, etc. — sufficient for all v1 features.

## [2026-07-07 11:08] Register Anthropic reference MCP servers globally at user scope
Category: tooling
Added filesystem, memory, sequential-thinking, fetch, git to `~/.claude.json` at user scope. Plus jupyter (HTTP `localhost:8888/mcp`) which activates once JupyterLab runs.
Rationale: user wanted a global "main" list. Available across all projects, not just this one.

## [2026-07-07 11:09] Correction: fetch and git are Python (uvx), not Node
Category: tooling
Initially registered `mcp-server-fetch` and `mcp-server-git` via `npx` — failed. Switched to `uvx mcp-server-fetch` and `uvx mcp-server-git`. Both now connected.
Rationale: those two reference servers ship as Python packages, not npm packages.

## [2026-07-07 11:10] Plan file location: dual (internal + project)
Category: process
Plan lives at both `~/.claude/plans/i-am-looking-to-humble-popcorn.md` (Claude Code internal) and `docs/PLAN.md` (checked in with code).
Rationale: user wanted the plan versioned with the project, not just in Claude's internal store.

## [2026-07-07 11:12] Dev environment: Homebrew + uv (no pipx)
Category: tooling
Replace `pipx run copier` with `uvx copier`. Use `uv venv` + `uv pip install -e ".[test]"` for the Python side. Node ≥ 20 already installed (v26.4.0).
Rationale: user's dev environment is brew + uv. `pipx` isn't installed and `uvx` is uv's equivalent one-shot tool runner. `uv pip` is faster than plain `pip` and respects the same lockfile.

## [2026-07-07 11:15] Haiku doc-keeper cron
Category: process
Haiku 4.5 agent runs every 10 minutes (durable, persists across sessions) reading `docs/DECISIONS.md` and updating `docs/PLAN.md`, `README.md`, `docs/CHANGELOG.md`, and `docs/Architecture.md` to reflect the current state.
Rationale: user wants documentation to stay in sync automatically without manual intervention. Haiku is cheap and fast enough for this maintenance work.

## [2026-07-07 11:40] Initial commit landed (6e4db50)
Category: process
Root commit `6e4db50` on `main` — 11 files, 335 insertions. Includes plan, decisions, doc-keeper cron config, uv init boilerplate, and stub. No Co-Authored-By trailer (user preference). `.claude/scheduled_tasks.lock` and `.claude/settings.local.json` excluded via `.gitignore`.
Rationale: capture baseline before Step 1 scaffold overwrites the working tree with copier output.

## [2026-07-07 11:57] JupyterLab extension scaffold generated
Category: tooling
Ran `uvx --with jinja2-time copier copy --trust https://github.com/jupyterlab/extension-template . --overwrite` (kind=frontend-and-server, has_settings=y, test=y, has_ai_rules=n). Template needed `jinja2-time` for `TimeExtension` — silent failure without it. Scaffold produced `jupyter_claude/` (Python), `src/` (TS), `schema/`, `install.json`, `package.json`, `pyproject.toml` (hatch + hatch-jupyter-builder), `.github/workflows/`, `ui-tests/` (Playwright/galata), `CONTRIBUTING.md`, `RELEASE.md`, `LICENSE` (BSD-3-Clause).
Rationale: JupyterLab's official template gives us build tooling, CI, and structure we'd otherwise hand-roll.

## [2026-07-07 12:00] Corrected labextension_name
Category: tooling
Copier picked `myextension@dc-ks/jupyter-claude` from my prompt answer `@dc-ks/jupyter-claude` — malformed (mixed case, missing scope prefix). Replaced with `@dckartasoft/jupyter-claude` (matches GitHub org `DCKartasoft`, all lowercase per NPM rules) across `package.json`, `pyproject.toml`, `schema/plugin.json`, `.copier-answers.yml`, `ui-tests/package.json`. `schema/plugin.json` title now reads "Jupyter Claude" for the human-facing Settings Editor entry.
Rationale: labextension name is the NPM package name; must be valid or `jlpm install` and Jupyter's labextension paths break.

## [2026-07-07 12:00] Changelog consolidation
Category: process
Deleted `docs/CHANGELOG.md`; root `CHANGELOG.md` (from copier, with `<START NEW CHANGELOG ENTRY>` markers used by `jupyter-releaser`) is now the single changelog. Doc-keeper cron retargeted (job `18c60a70` replaces `63492d24`) to write inside those markers.
Rationale: JupyterLab convention. Two changelogs is confusing; `jupyter-releaser` won't find our decisions if they're in `docs/`.

## [2026-07-07 12:00] Stubs removed
Category: cleanup
Deleted `main.py` (uv init boilerplate) and `Jupyter-Claude-Plug.py` (empty Day-1 stub). Both superseded by the copier scaffold.
Rationale: dead files.

## [2026-07-07 12:15] Server extension built (Step 2)
Category: architecture
Added `jupyter_claude/config.py` (`ClaudeExtensionApp(ExtensionApp)` with traits: backend, model, aws_region, system_prompt, jupyter_mcp_url, permission_mode, verbose), `agent.py` (`build_options()` returns `ClaudeAgentOptions` wired to Jupyter MCP), and `chat_handler.py` (`ChatWebSocketHandler`, one SDK client per WS connection). `__init__.py` now registers via `{"module": "jupyter_claude", "app": ClaudeExtensionApp}` — the ExtensionApp `initialize_handlers` binds `/jupyter-claude/hello` (kept for smoke tests) and `/jupyter-claude/chat` (WebSocket). Backend selection is env-var driven at query time; users configure via `jupyter_server_config.py` or the JupyterLab Settings Editor (schema/plugin.json mirrors the traits).
Rationale: ExtensionApp is the future-proof path (matches jupyter-ai); per-WS SDK client is the simplest session model for v1 and matches the SDK's `async with` idiom.

## [2026-07-07 12:15] Stale malformed name refs cleaned up
Category: cleanup
Fixed remaining `myextension@dc-ks/jupyter-claude` references in `jupyter_claude/__init__.py`, `src/index.ts`, `src/__tests__/jupyter_claude.spec.ts`, `ui-tests/tests/jupyter_claude.spec.ts`, `CONTRIBUTING.md`. The earlier fix in Step 1 only covered JSON/YAML/TOML; missed Python/TS/MD.
Rationale: leftover refs would break plugin ID matching in the frontend activate hook and integration tests.

## [2026-07-07 12:45] Frontend built (Step 3)
Category: architecture
Added `src/ws.ts` (typed WebSocket client with auto-reconnect and message-queue buffering), `src/panel.tsx` (React chat UI wrapped in a `ReactWidget`, plain scrolling message list + textarea input; message roles rendered as user/assistant/tool/system), `src/commands.ts` (four commands: `jclaude:open-chat`, `jclaude:generate-cell`, `jclaude:explain-cell`, `jclaude:fix-last-error`; command palette entries + cell context-menu entries; `NotebookActions.executed` capture stores last error per notebook). `src/index.ts` requires `INotebookTracker` and `ILabShell`, activates on app.restored and attaches the panel to the right sidebar. `schema/plugin.json` adds `jupyter.lab.toolbars` entries for a Cell-toolbar "Explain" button and a Notebook-toolbar "Open Chat" button. `style/base.css` styles the panel using JupyterLab CSS variables so it themes with light/dark.
Rationale: matches the plan (right-side panel, four v1 commands). Simple message list, no `@jupyter/chat` dependency, no Yjs — deferred per plan.

## [2026-07-07 12:45] React 18 pinned; tsconfig moduleResolution=bundler
Category: dependency
`jlpm add react react-dom` initially pulled React 19.2.7, which broke type-compat with `@jupyterlab/apputils`'s bundled `@types/react` 18.x — `ReactWidget.render()` returns `ReactRenderElement | null`, incompatible with React 19's `ReactElement`. Pinned to `react@^18.2.0` and `react-dom@^18.2.0` (both runtime and types). Separately, `tsconfig.json` `moduleResolution` was `node`, which couldn't resolve `vscode-languageserver-protocol` from `@jupyterlab/lsp`. Switched to `moduleResolution: bundler` (with `module: esnext`) — JupyterLab 4's current recommendation. `node16` was too strict (ESM/CJS interop errors from `@jupyter/ydoc`).
Rationale: forced by JupyterLab 4's typings. Pin now, revisit when JupyterLab bundles React 19.

## [2026-07-07 12:45] Frontend cell-write path: MCP tool calls, not local insertion
Category: architecture
For the three cell-manipulating commands (generate/explain/fix), the frontend sends a prompt to Claude with an explicit instruction to use `mcp__jupyter__insert_execute_code_cell` (or `insert_cell` + `execute_cell`). Claude writes to the notebook via the Jupyter MCP server; the frontend does not parse fenced code blocks itself. This is the opposite of what the earlier PLAN.md draft suggested (simple path = frontend parses text).
Rationale: cleaner separation. Claude sees the exact notebook state via `read_notebook` and writes back through the same MCP surface, so cell positions and outputs stay consistent. Frontend stays simple — it just streams chat.

## [2026-07-07 13:00] Bedrock config expanded: SSO profile + per-tier model IDs
Category: architecture
User's target environment uses shared AWS SSO with `AWS_PROFILE=<name>` and the Claude Code convention of three tier defaults: `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`. Added four new traits to `ClaudeExtensionApp`: `aws_profile`, `default_opus_model` (default `us.anthropic.claude-opus-4-7`), `default_sonnet_model` (default `us.anthropic.claude-sonnet-4-6`), `default_haiku_model` (default `us.anthropic.claude-haiku-4-5-20251001-v1:0`). `build_options()` in `agent.py` now sets the three tier env vars (not a single `ANTHROPIC_MODEL`) and injects `AWS_PROFILE` from the trait, still forwarding any AWS creds already in the process env (`AWS_CONFIG_FILE`, `AWS_SHARED_CREDENTIALS_FILE` added to the forward list for SSO cache discovery). `schema/plugin.json` mirrors the traits; README documents the `aws-vault exec` launch pattern.
Rationale: the user's existing shell alias (`AWS_PROFILE=... AWS_REGION=... claude`) is a CLI-specific hack that doesn't survive being run under Jupyter. Making profile + per-tier models first-class traits means users configure once (Settings Editor or `jupyter_server_config.py`), and Jupyter itself can be launched with `aws-vault exec <profile> -- jupyter lab` to inject temporary STS credentials without leaking secrets to disk.

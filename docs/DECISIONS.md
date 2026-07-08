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

## [2026-07-07 15:17] Labextension linked as symlink via `jupyter labextension develop`
Category: tooling
The initial `uv pip install -e ".[dev,test]"` shipped the pre-copier bundle into `.venv/share/jupyter/labextensions/@dckartasoft/jupyter-claude/` and it was never refreshed. All `jlpm build` runs updated the in-tree `jupyter_claude/labextension/` but Jupyter served the stale copy. Diagnosed after the browser showed the old plugin ID `myextension@dc-ks/jupyter-claude` in activation logs. Fix: `jupyter labextension develop . --overwrite` replaces the .venv path with a symlink to the in-tree build. Also had to clear `~/.jupyter/lab/workspaces/*.jupyterlab-workspace` (stale layout with old widget list) and add `ILayoutRestorer` to the plugin so the right-sidebar attachment survives future workspace persistence.
Rationale: development workflow needs the symlink; without it every source change requires a manual copy or full re-install. Add `jupyter labextension develop` to the README dev-install block.

## [2026-07-07 15:20] `page_config.json` disabled/locked our extension
Category: tooling
`.venv/etc/jupyter/labconfig/page_config.json` had `disabledExtensions.dckartasoft-jupyter-claude=true` AND `lockedExtensions.dckartasoft-jupyter-claude=true` — presumably left over from an earlier `jupyter labextension disable` run during the malformed-name era. Result: extension showed as `enabled OK` in `jupyter labextension list` but `activate()` never ran (silently). Cleared both maps.
Rationale: don't `disable` the extension by NPM name during development — restart with a rebuild instead.

## [2026-07-07 15:40] Icon: `codeIcon` (no `chatIcon` in ui-components)
Category: architecture
`ChatPanelWidget.title` needs `.icon` set for the sidebar tab to render. Initially tried `chatIcon` from `@jupyterlab/ui-components` — doesn't exist. Used `codeIcon` (available in `iconimports`).
Rationale: sidebar tabs without an icon render as a zero-width strip.

## [2026-07-07 15:45] Command dialogs use JupyterLab InputDialog
Category: architecture
`window.prompt()` was silently blocked by the browser in the JupyterLab iframe context — Test 2 (`Generate cell`) appeared to do nothing. Also `Fix last error` command never showed in the palette because `isEnabled` checked `lastErrors.has(notebook.id)` but the executed-cell signal keys the notebook differently — the lookup always missed. Fixes: swap `window.prompt` → `InputDialog.getText` (real JupyterLab modal); key `lastErrors` by `tracker.currentWidget?.id` consistently at both write and read; always enable `Fix last error` when a notebook is open (friendly dialog if no error captured yet); added `console.log` when an error is captured for debugging.
Rationale: needed to be able to test the commands at all; and the fix-last-error id mismatch was blocking every future user, not just first-run.

## [2026-07-07 15:50] Cell-type dropdown for Generate command
Category: architecture
`Generate cell with Claude…` now opens a first dialog with a dropdown (`code` / `markdown` / `raw`, default `code`), then a description dialog whose placeholder adapts to the chosen type. Prompt sent to Claude differs by type: code cells → `mcp__jupyter__insert_execute_code_cell`; markdown/raw → `mcp__jupyter__insert_cell` with `cell_type="..."` and an explicit "do not execute" instruction.
Rationale: user requested. Also more accurate — markdown/raw cells shouldn't go through `insert_execute_code_cell` which auto-runs.

## [2026-07-07 15:53] `main_model_tier` trait for speed/quality tradeoff
Category: architecture
Response time on Opus 4.7 felt slow. Added `main_model_tier: Enum(["opus", "sonnet", "haiku"], default="sonnet")` trait. `agent.py` now writes `ANTHROPIC_MODEL` (in addition to the three tier vars) to the selected tier's model ID; `chat_handler.py` sends that resolved model back in the `ready` frame so the panel's "Connected — bedrock / …" line shows what's actually running. Schema entry added. Bedrock only — Anthropic direct still uses the plain `model` trait.
Rationale: Sonnet 4.6 is a good default for chat/cell generation (2-3× faster than Opus, comparable quality on this workload). Users who want max quality can flip to opus; users who want max speed can flip to haiku.

## [2026-07-07 15:53] Panel spinner + command-triggered busy state
Category: architecture
Added a "Claude is thinking…" row with an animated spinner while `busy=true`. Previously, prompts sent from commands (`chatPanel.sendMessage(...)`) bypassed the panel state and never set busy — no visual feedback until the response streamed in. Fix: `sendMessage()` now routes through an internal `submit` callback that both appends the user message and sets busy, matching the input-field submit path.
Rationale: the panel needs to look alive during long generations, especially for command flows where the user doesn't type into the input.

## [2026-07-07 16:05] Runtime model selector in chat panel
Category: architecture
Added a `<select>` at the top of the chat panel with `opus`/`sonnet`/`haiku` options. Selection sends `{"type": "set_tier", "tier": "..."}` over the WebSocket; the chat handler closes and reopens the SDK client with the new tier via a new `tier_override` kwarg on `build_options()`. Server-side `ChatWebSocketHandler` now tracks `_tier` per connection and exposes `_start_client`/`_stop_client` helpers. `ready` frame gained a `tier` field so the UI reflects the active tier without re-parsing the model ID. Dropdown is disabled when backend is not `bedrock` (Anthropic direct uses the `model` trait, not tiers) or while a request is in flight.
Rationale: users want per-conversation control over quality/speed without editing `jupyter_server_config.py`. Cost: switching resets conversation history (SDK is per-connection). Session `resume=` support could restore continuity — deferred.

## [2026-07-07 16:05] Full command set on notebook toolbar
Category: architecture
`schema/plugin.json` now registers all four Claude commands in the notebook toolbar (ranks 60-63): Open Chat, Generate cell, Explain cell, Fix last error. Each command has an `icon` property so it renders as an icon-only toolbar button with a tooltip: `claudeIcon` (chat), `addIcon` (generate), `editIcon` (explain), `bugIcon` (fix). Cell toolbar keeps just Explain (rank 60) since Generate/Fix aren't cell-scoped.
Rationale: user requested. Toolbar buttons are faster than palette lookup for frequent actions. Icons make the four functions discoverable at a glance.

## [2026-07-07 16:05] Custom `claudeIcon` (blue SVG spark)
Category: architecture
New `src/icons.ts` exports `claudeIcon = new LabIcon({name, svgstr})` — an inline SVG showing a stylised blue 4-point spark (`#4361ee`) with a small companion mark. Replaces the built-in `codeIcon` on the sidebar tab, the Open Chat toolbar button, and the palette entry. Custom LabIcon avoids the need for a separate PNG/SVG file in the extension bundle.
Rationale: user asked for the blue Claude-style icon instead of the generic `< >` code icon. `@jupyterlab/ui-components` doesn't ship a Claude/Anthropic mark; `LabIcon.svgstr` is the sanctioned path for custom icons. Colour is hard-coded; can be moved to a CSS variable if theming becomes needed.

## [2026-07-07 16:20] MCP server enumeration + runtime selector
Category: architecture
Added `jupyter_claude/mcp_discovery.py` (`list_user_mcp_servers()` reads `~/.claude.json` `mcpServers` map), `enabled_mcp_servers: List(Unicode)` trait on `ClaudeExtensionApp` (default `["jupyter"]`), and two REST endpoints under `/jupyter-claude/mcp-servers` (GET returns list with description + enabled + required flags; POST persists selection). `agent.py`'s `_build_mcp_servers()` now assembles the SDK's `mcp_servers` dict from user config filtered by `enabled_mcp_servers` — `jupyter` is always included. `_allowed_tools_for()` generates `[f"mcp__{name}__*" for name in servers]` so only the enabled server namespaces are exposed to Claude. New `mcp_reload` WS frame restarts the SDK client with the fresh filter. Frontend: `src/mcpDialog.tsx` (React checkbox list wrapped in a `Dialog`) fetches via GET, saves via POST, then sends `mcp_reload`. New command `jclaude:mcp-servers` (extensionIcon) in palette + notebook toolbar.
Rationale: user's `~/.claude.json` has 18 servers (mostly AWS/Azure clouds), each spawns a subprocess on SDK startup; startup lag was noticeable and Claude sees hundreds of tools it doesn't need. `enabled_mcp_servers` defaults to just `["jupyter"]` — everything else opt-in per session via the dialog.

## [2026-07-07 16:35] User guide added at `docs/USER_GUIDE.md`
Category: process
Wrote a user-facing install and operation guide covering: requirements, install (`uv` + `jlpm build` + `jupyter labextension develop`), the two backend paths (Anthropic direct with `ANTHROPIC_API_KEY`, Bedrock via SSO profile with per-tier model IDs), launch, using each of the five commands (open chat / generate / explain / fix / MCP servers), full trait reference table with defaults, troubleshooting (stale `page_config.json` disabled/locked lists, SSO expiry, missing kernel), and uninstall. Cross-linked from `README.md`.
Rationale: `README.md` covers overview + quickstart; `CONTRIBUTING.md` covers hacking on the extension. Neither is a user manual. Onboarding a colleague to the plugin needs a single file that walks from `git clone` through "your first chat", including the gotchas we hit during Step 5 verification (page_config.json disable was the biggest time sink).

## [2026-07-08 09:15] SageMaker deployment section added to `docs/USER_GUIDE.md`
Category: process
Added a "Running on AWS SageMaker" section covering: which SageMaker environment works (Studio JupyterLab 4 supported; Studio Classic and old Notebook Instances not without a JL3 port), required IAM permissions (`bedrock:InvokeModel` + `InvokeModelWithResponseStream` + `ListInferenceProfiles` + `GetInferenceProfile`), a full setup script for Studio lifecycle config or terminal (installs Node 20 + Claude Code CLI + Python deps + extension + `jupyter_server_config.py`), and SageMaker-specific gotchas (leave `aws_profile` empty so IAM role is used, `jupyter labextension develop` links are ephemeral in Studio envs, region-specific model IDs, no egress rules needed for Bedrock).
Rationale: user asked whether the extension runs in SageMaker. It does with three real caveats (JL4 only, Claude Code CLI must be installed, extension link is ephemeral). Rather than answer once in chat, capture the deployment recipe in the guide so future users find it.

## [2026-07-08 10:55] PyPI publish prep — package renamed `jupyter-claude-plugin`, version 0.1.0a1
Category: tooling
Renamed the PyPI project name to `jupyter-claude-plugin` (was `jupyter_claude` — too generic and clashy on PyPI). Internal Python package dir stays `jupyter_claude`; only the distribution name changed. Version bumped to `0.1.0-alpha.1` in `package.json` (PEP 440 canonicalizes to `0.1.0a1`) — signals pre-release so `pip install jupyter-claude-plugin` doesn't grab it without `--pre`. Added `claude-agent-sdk>=0.1`, `jupyter-mcp-server>=1.0`, `jupyter-collaboration>=2.0` to `[project].dependencies` (previously only `jupyter_server` was declared; users had to install runtime deps manually). Moved URLs out of `dynamic` into an explicit `[project.urls]` block (Homepage / Documentation / Repository / Issues / Changelog). Added extra classifiers (Development Status Alpha, Intended Audience, Operating System, Topic). Fixed a build bug: hatchling couldn't auto-discover the wheel package after the rename — added `[tool.hatch.build.targets.wheel] packages = ["jupyter_claude"]`. Verified the resulting wheel (`jupyter_claude_plugin-0.1.0a1-py3-none-any.whl`, 111 KB, 31 files) installs cleanly in a scratch venv: `jupyter server extension list` shows `jupyter_claude 0.1.0a1 OK`, `jupyter labextension list` shows `@dckartasoft/jupyter-claude v0.1.0-alpha.1 enabled OK`, and all runtime imports resolve. Updated `README.md` and `docs/USER_GUIDE.md` install sections to prefer `pip install --pre jupyter-claude-plugin` over source install; source install becomes the dev path. SageMaker setup script in USER_GUIDE simplified to a one-line pip install.
Rationale: publishing to PyPI turns the SageMaker install from a git clone + Node + jlpm build ordeal into a single `pip install`. Alpha designator (`0.1.0a1`) protects users from a broken preview while letting early adopters opt in with `--pre`. Renaming to `jupyter-claude-plugin` avoids collision with any future generic Jupyter+Claude package and matches the pattern of other JupyterLab extension packages on PyPI.

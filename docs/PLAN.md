# Claude Collaborator for JupyterLab — Implementation Plan

## Context

You want a JupyterLab extension that lets a user collaborate with Claude on notebook code and documentation. Four v1 interactions: (1) chat about the notebook, (2) generate a new cell from a prompt, (3) explain / document an existing cell, (4) fix the last cell error. Claude runs via the **Claude Agent SDK** (Python), which can dispatch to either **Anthropic direct** or **AWS Bedrock** based on env vars. The plugin uses **MCP** on both sides:

- **Jupyter MCP server** (`jupyter-mcp-server` by Datalayer) — exposes cell read/write/execute tools to Claude
- **Anthropic reference MCP servers** — registered globally at user scope so Claude Code (and this plugin's SDK client) can call them everywhere

Working directory `/Users/DC-KS/Dev/Jupyter-Claude_Plugin` is empty except for a stub `Jupyter-Claude-Plug.py`. We scaffold fresh.

## Architecture

```
JupyterLab (browser)
  └─ Frontend extension (TS/React)
       ├─ Right-side chat panel      ── WS ──┐
       ├─ Cell toolbar buttons                │
       └─ Context-menu items                  ▼
                                    Server extension (Python, in-process)
                                       └─ WebSocket handler /jclaude/chat
                                            └─ ClaudeSDKClient (async)
                                                 ├─ backend: Anthropic API | Bedrock (env-var)
                                                 └─ mcp_servers.jupyter → http://localhost:8888/mcp
                                                                          (jupyter-mcp-server extension,
                                                                           same process)
```

Claude reads / writes / executes cells via `mcp__jupyter__*` tools — we do **not** hand-roll cell tools. The only custom tool is `stream_cell_delta` (below).

## Step 0 — Register MCP servers globally (before writing code)

Run at user scope (`~/.claude.json`):

```bash
# Anthropic reference servers (per user selection)
claude mcp add --scope user filesystem -- npx -y @modelcontextprotocol/server-filesystem $HOME
claude mcp add --scope user memory -- npx -y @modelcontextprotocol/server-memory
claude mcp add --scope user sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking
claude mcp add --scope user fetch -- npx -y @modelcontextprotocol/server-fetch
claude mcp add --scope user git -- npx -y @modelcontextprotocol/server-git

# Jupyter MCP (used by the plugin's SDK client; also handy from Claude Code)
claude mcp add --scope user jupyter --transport http http://localhost:8888/mcp
```

Verify with `claude mcp list`.

## Step 1 — Scaffold the extension

Dev env uses **Homebrew + uv** (no pipx). Use `uvx` as the pipx equivalent. Create/activate a project venv first so all installs land in one place:

```bash
cd /Users/DC-KS/Dev/Jupyter-Claude_Plugin
uv venv                      # creates .venv/ with the interpreter uv picks
source .venv/bin/activate

# Scaffold with copier via uvx (one-shot tool run — no global install)
uvx --from "copier" --with "copier-templates-extensions" \
  copier copy --trust https://github.com/jupyterlab/extension-template . --overwrite
```

Choose `kind: frontend-and-server`, package name `jupyter_claude`, author metadata, license. This produces the standard layout: `pyproject.toml`, `package.json`, `src/index.ts`, `jupyter_claude/__init__.py`, `jupyter_claude/handlers.py`, `schema/plugin.json`, `jupyter-config/`, `install.json`. Delete the stub `Jupyter-Claude-Plug.py`.

Install dev deps (uv-native, keeps `pyproject.toml` as the source of truth):

```bash
jlpm install                                                    # frontend deps
uv pip install -e ".[dev,test]"                                 # editable install of the extension
uv pip install jupyter-mcp-server jupyter-collaboration claude-agent-sdk

# Link the labextension so Jupyter serves in-tree builds (required for dev)
jupyter labextension develop . --overwrite
jupyter server extension enable jupyter_claude
```

Prereq: Node ≥ 20 (`brew install node`) — the copier template's build (`jlpm build`) needs it.

## Step 2 — Server extension (Python)

**Files:** [jupyter_claude/handlers.py], [jupyter_claude/agent.py] (new), [jupyter_claude/config.py] (new), [jupyter_claude/mcp_discovery.py] (new), [jupyter_claude/__init__.py].

- `config.py` — a `jupyter_server.extension.application.ExtensionApp` traitlets class exposing:
  - `backend: Enum("anthropic", "bedrock")`
  - `model: Unicode` (e.g. `us.anthropic.claude-opus-4-8` for Bedrock, `claude-opus-4-8` for Anthropic direct)
  - `aws_region: Unicode` (Bedrock only)
  - `aws_profile: Unicode` (Bedrock only; named AWS SSO profile from `~/.aws/config`; profile and region are forwarded to the SDK subprocess)
  - `default_opus_model`, `default_sonnet_model`, `default_haiku_model: Unicode` (Bedrock; inference-profile IDs; defaults: `us.anthropic.claude-opus-4-7`, `us.anthropic.claude-sonnet-4-6`, `us.anthropic.claude-haiku-4-5-20251001-v1:0`)
  - `main_model_tier: Enum(["opus", "sonnet", "haiku"], default="sonnet")` (Bedrock only; speed/quality tradeoff; resolved tier's model ID is set as `ANTHROPIC_MODEL`)
  - `enabled_mcp_servers: List(Unicode)` (default `["jupyter"]`; which servers from `~/.claude.json` should be active; used to filter `allowed_tools`)
  - `system_prompt: Unicode`
  - Overridable via `jupyter_server_config.py` **and** the JupyterLab Settings Editor (schema mirrored in `schema/plugin.json`).
- `agent.py` — `build_options(cfg, jupyter_token, tier_override=None) → ClaudeAgentOptions`:
  - Builds SDK environment dict with backend selection (env vars for Bedrock, ANTHROPIC_API_KEY left in env for Anthropic direct).
  - For Bedrock, sets `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL` and optionally `ANTHROPIC_MODEL` for the chosen tier (defaults to `cfg.main_model_tier`, overridable via `tier_override` when user switches in chat panel).
  - Assembles `mcp_servers` dict filtered by `cfg.enabled_mcp_servers` (always includes `jupyter`).
  - Returns `ClaudeAgentOptions` with `allowed_tools=[f"mcp__{name}__*" for name in enabled_servers]` — restricts Claude to only the user-enabled MCP namespaces.
- `mcp_discovery.py` — `list_user_mcp_servers() → List[Dict]`:
  - Reads `~/.claude.json` and extracts `mcpServers` map.
  - Returns list of server dicts with `{name, description, enabled, required_status}` for each server.
- `handlers.py` — multiple WebSocket and REST endpoints:
  - WebSocket handler at `/jupyter-claude/chat`. Per-connection state with `_client` (async ClaudeSDKClient), `_tier` (active tier for Bedrock).
    - Inbound WS messages: `{type: "user_message", text, notebook_ctx}` → `await client.query(prompt)`; `{type: "approve", tool_use_id, allow}` → resolves permission promise; `{type: "set_tier", tier}` → `_stop_client()`, rebuild options with new tier, `_start_client()`.
    - Outbound: stream every `TextBlock` / `ToolUseBlock` / `ResultMessage` as JSON frames. `ready` frame includes active `tier` field.
  - REST GET `/jupyter-claude/mcp-servers` — returns list of available servers with `{name, description, enabled, required}` flags.
  - REST POST `/jupyter-claude/mcp-servers` — persists updated `enabled_mcp_servers` list to extension traits; returns 200 on success.
- `__init__.py` — expose `_jupyter_server_extension_points()` returning the ExtensionApp; template already wires `_jupyter_labextension_paths()`.

**Reuse:** `jupyter-mcp-server` runs as a Jupyter server extension in the same process — no subprocess management. It exposes `mcp__jupyter__{read_cell, insert_cell, overwrite_cell_source, execute_cell, insert_execute_code_cell, read_notebook, list_notebooks, use_notebook, ...}` — sufficient for all four v1 interactions.

## Step 3 — Frontend extension (TS/React)

**Files:** [src/index.ts], [src/panel.tsx] (new), [src/commands.ts] (new), [src/ws.ts] (new), [schema/plugin.json].

- `src/index.ts` — one `JupyterFrontEndPlugin<void>`. Requires `INotebookTracker`, `ILabShell`, `ISettingRegistry`, `ICommandPalette`. On activate:
  - Register commands (see `commands.ts`).
  - Create a `ReactWidget` chat panel, `app.shell.add(widget, 'right', { rank: 900 })`.
  - Attach `NotebookActions.executed.connect(onCellExecuted)` — capture `{success:false, error}` and buffer the last error per notebook for the "Fix last error" command.
- `src/commands.ts` — five commands, each posts a WS message with the right prompt template and instructs Claude to use `mcp__jupyter__*` tools:
  - `jclaude:open-chat` (open panel; palette + notebook toolbar button)
  - `jclaude:generate-cell` (modal to choose cell type; sends prompt with instruction to call `mcp__jupyter__insert_execute_code_cell` or `insert_cell` per type)
  - `jclaude:explain-cell` (cell context menu + toolbar; reads source, sends prompt with instruction to call `mcp__jupyter__insert_cell` above)
  - `jclaude:fix-last-error` (palette + notebook toolbar; uses buffered error; instructs Claude to use `mcp__jupyter__insert_cell` or `insert_execute_code_cell` below)
  - `jclaude:mcp-servers` (palette + notebook toolbar; opens MCP server selector dialog)
  - Register on toolbars via `schema/plugin.json` `"jupyter.lab.toolbars"` and context menu via `app.contextMenu.addItem()`.
- `src/panel.tsx` — chat UI: scrolling message list (user/assistant/tool/system roles), animated spinner while busy, runtime tier selector (`<select>` disabled for Anthropic direct or mid-request), input textarea. Wire markdown rendering via `@jupyterlab/rendermime`. Do **not** pull in `@jupyter/chat` for v1 (Yjs shared-doc storage is overkill).
- `src/mcpDialog.tsx` — React dialog for MCP server selector: checkbox list of servers, GET `/jupyter-claude/mcp-servers` to fetch, POST to persist, send `mcp_reload` on change.
- `src/ws.ts` — thin wrapper around `new WebSocket(URLExt.join(ServerConnection.makeSettings().wsUrl, 'jclaude/chat'))` with auto-reconnect and typed message events.
- `schema/plugin.json` — settings schema mirroring `config.py` traits (backend, model, aws_region, system_prompt) so users edit them in Settings Editor.

**Cell-write path:** Claude calls `mcp__jupyter__insert_cell` (or `insert_execute_code_cell`) directly via the Jupyter MCP server for all cell-manipulating commands. Frontend does not parse fenced code blocks; it streams chat and watches the notebook update via MCP. Cleaner separation: Claude sees exact notebook state via `read_notebook` and writes back through the same MCP surface, keeping cell positions and outputs consistent.

## Step 4 — Optional custom tool for streaming diffs (defer)

Only if we want token-by-token fill-in of a cell being generated: add `@tool("stream_cell_delta", "...", {"cell_id": str, "delta": str})` via `create_sdk_mcp_server` and push deltas back over the WS. Skip in v1.

## Step 5 — Verification

1. **MCP registration** — `claude mcp list` shows filesystem, memory, sequential-thinking, fetch, git, jupyter.
2. **Backend switching** — start with `JupyterClaudeApp.backend = "anthropic"` + `ANTHROPIC_API_KEY`, send a chat message, verify response. Switch to `backend = "bedrock"` + `AWS_REGION=us-east-1` + `ANTHROPIC_MODEL=us.anthropic.claude-opus-4-8`, verify the same query works (needs `bedrock:InvokeModel` IAM).
3. **Per-feature smoke test** in `jupyter lab`:
   - Open panel from right sidebar. Ask "what does this notebook do?" — Claude should invoke `mcp__jupyter__read_notebook`.
   - Cell toolbar → Explain — a markdown cell appears above with a description.
   - Palette → Generate → "load iris.csv into a DataFrame" — a code cell appears below with working code; run it.
   - Trigger an error in a cell (`1/0`), then palette → Fix last error — a corrected cell appears.
4. **MCP tool visibility** — inspect the first `SystemMessage(subtype="init")` from the SDK; `message.data["mcp_servers"]["jupyter"].tools` must include the cell R/W tools.
5. **Permission gating** — verify `permission_prompt_tool_name="jclaude_approve"` fires a modal in the panel before Claude writes/executes a cell for the first time in a session.

## Critical files to touch

| File | Purpose |
|---|---|
| [jupyter_claude/config.py] | Backend + model + AWS region + MCP traitlets |
| [jupyter_claude/agent.py] | Build `ClaudeAgentOptions`, filter MCP servers by enabled list |
| [jupyter_claude/mcp_discovery.py] | List user's registered MCP servers from `~/.claude.json` |
| [jupyter_claude/handlers.py] | WS chat handler, REST MCP-servers endpoints, tier switching |
| [jupyter_claude/__init__.py] | Extension entrypoints |
| [src/index.ts] | Plugin activate, tracker + shell wiring |
| [src/commands.ts] | Five v1 commands + cell-error capture |
| [src/panel.tsx] | React chat panel with tier selector + spinner |
| [src/mcpDialog.tsx] | MCP server selector dialog |
| [src/ws.ts] | WS client with typed messages |
| [src/icons.ts] | Custom `claudeIcon` SVG |
| [schema/plugin.json] | Toolbar registration + settings schema |
| [pyproject.toml] | Add `claude-agent-sdk`, `jupyter-mcp-server`, `jupyter-collaboration` |

## Out of scope for v1

- Yjs / `@jupyter/chat` shared-doc chat storage (defer)
- Streaming code deltas into a live-editing cell (Step 4, defer)
- Multi-notebook session memory / persistent history
- Custom prompt templates per language / kernel type

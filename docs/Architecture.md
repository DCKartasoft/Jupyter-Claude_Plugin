# Architecture

_Living overview. Maintained by the doc-keeper from [DECISIONS.md](DECISIONS.md)._

## Component diagram

```
JupyterLab (browser)
  └─ Frontend extension (TS/React)
       ├─ Right-side chat panel        ── WS ──┐
       │   ├─ Runtime tier selector (opus/sonnet/haiku, Bedrock only)
       │   ├─ Message list (user/assistant/tool/system roles)
       │   ├─ Animated spinner ("Claude is thinking…" while busy)
       │   └─ Input textarea
       ├─ Notebook toolbar buttons (4 commands, icons)
       ├─ Cell toolbar (Explain command)
       └─ Context-menu items                   ▼
                                    Server extension (Python, in-process)
                                       └─ WebSocket handler /jclaude/chat
                                            └─ ClaudeSDKClient (async, per connection)
                                                 ├─ backend: Anthropic API | Bedrock (env-var)
                                                 └─ mcp_servers.jupyter → http://localhost:8888/mcp
                                                                          (jupyter-mcp-server extension,
                                                                           same process)
```

## UI elements

- **Custom icon** (`claudeIcon`): blue SVG spark (`#4361ee`) marks the sidebar tab and Open Chat toolbar button.
- **Tier selector** (Bedrock only): dropdown in panel header; sends `set_tier` message to toggle between opus/sonnet/haiku; connection is closed and reopened with the new tier; disabled for Anthropic direct or while a request is in flight.
- **MCP server selector** (extensionIcon): command in palette + notebook toolbar; opens checkbox dialog to enable/disable individual servers from `~/.claude.json` (default: `["jupyter"]`); sends `mcp_reload` to restart SDK client with new filter.
- **Spinner** (`busy=true`): animated indicator while Claude processes a prompt (from typed input or command-triggered message).
- **Commands**: five toolbar buttons (notebook: Open Chat, Generate, Explain, Fix, MCP Servers; cell: Explain) with icon+tooltip and palette entries.

## Data flow

1. User types in chat panel (or clicks a cell toolbar button).
2. Frontend sends JSON over WebSocket to `/jclaude/chat`.
3. Server handler forwards prompt to `ClaudeSDKClient`.
4. Claude reads/writes/executes cells via `mcp__jupyter__*` tools (Jupyter MCP server, same process).
5. Assistant messages stream back to the panel over the same WebSocket.

## Backend selection

Backend is env-var driven inside the Agent SDK at query time:

- **Anthropic direct**: `ANTHROPIC_API_KEY` in process env; uses model IDs like `claude-opus-4-8`; `model` trait picked from config.

- **AWS Bedrock**: `CLAUDE_CODE_USE_BEDROCK=1` + `AWS_REGION` + AWS credentials + AWS SSO profile name. Server extension sets:
  - `ANTHROPIC_DEFAULT_OPUS_MODEL` (default `us.anthropic.claude-opus-4-7`)
  - `ANTHROPIC_DEFAULT_SONNET_MODEL` (default `us.anthropic.claude-sonnet-4-6`)
  - `ANTHROPIC_DEFAULT_HAIKU_MODEL` (default `us.anthropic.claude-haiku-4-5-20251001-v1:0`)
  - `ANTHROPIC_MODEL` to the selected tier's inference-profile ID (active tier resolved from `main_model_tier` trait or user's runtime selection)
  - `AWS_PROFILE` from `aws_profile` trait; enables shared AWS SSO lookup.

Default tier is `main_model_tier` trait (default `sonnet`); user can switch per-conversation via the tier selector in the chat panel. Configuration is set via `jupyter_server_config.py` or the JupyterLab Settings Editor (schema in `schema/plugin.json`).

## MCP tool visibility

The server extension reads `enabled_mcp_servers` trait (list of server names enabled per session; default `["jupyter"]`) and builds the SDK's `allowed_tools` filter as `[f"mcp__{name}__*" for name in enabled_servers]`. This restricts Claude's tool calls to only the user-enabled MCP namespaces, reducing startup lag and preventing tool confusion from hundreds of unused servers. Jupyter MCP server is always included. User can toggle server membership at runtime via the MCP selector dialog in the chat panel; selection change triggers `mcp_reload` to restart the SDK client with the new filter (conversation history is reset).

## MCP tool usage

Claude reads / writes / executes cells via `mcp__jupyter__*` tools provided by `jupyter-mcp-server`:

- `read_notebook` — current notebook state
- `read_cell` — single cell source
- `insert_cell`, `insert_execute_code_cell` — add new cell (with or without auto-execution)
- `overwrite_cell_source` — modify existing cell
- `execute_cell` — run a cell and capture output

Frontend does not parse code blocks; it sends prompts with explicit instructions for Claude to use these tools. Frontend streams chat messages and watches the notebook update via MCP, keeping state consistent.

# Architecture

_Living overview. Maintained by the doc-keeper from [DECISIONS.md](DECISIONS.md)._

## Component diagram

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

## Data flow

1. User types in chat panel (or clicks a cell toolbar button).
2. Frontend sends JSON over WebSocket to `/jclaude/chat`.
3. Server handler forwards prompt to `ClaudeSDKClient`.
4. Claude reads/writes/executes cells via `mcp__jupyter__*` tools (Jupyter MCP server, same process).
5. Assistant messages stream back to the panel over the same WebSocket.

## Backend selection

Backend is env-var driven inside the Agent SDK at query time:
- `ANTHROPIC_API_KEY` → Anthropic direct (uses model IDs like `claude-opus-4-8`)
- `CLAUDE_CODE_USE_BEDROCK=1` + `AWS_REGION` + AWS credentials → AWS Bedrock (requires inference-profile model IDs like `us.anthropic.claude-opus-4-8`)

Configuration is set via `jupyter_server_config.py` or the JupyterLab Settings Editor (schema in `schema/plugin.json`).

## MCP tool usage

Claude reads / writes / executes cells via `mcp__jupyter__*` tools provided by `jupyter-mcp-server`:
- `read_notebook` — current notebook state
- `read_cell` — single cell source
- `insert_cell`, `insert_execute_code_cell` — add new cell (with or without auto-execution)
- `overwrite_cell_source` — modify existing cell
- `execute_cell` — run a cell and capture output

Frontend does not parse code blocks; it sends prompts with explicit instructions for Claude to use these tools. Frontend streams chat messages and watches the notebook update via MCP, keeping state consistent.

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

Backend is env-var driven inside the Agent SDK:
- `ANTHROPIC_API_KEY` → Anthropic direct
- `CLAUDE_CODE_USE_BEDROCK=1` + `AWS_REGION` + AWS creds → Bedrock (requires cross-region inference-profile model IDs like `us.anthropic.claude-opus-4-8`)

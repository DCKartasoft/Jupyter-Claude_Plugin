# Jupyter Claude Plugin

[![Github Actions Status](https://github.com/DCKartasoft/Jupyter-Claude_Plugin/workflows/Build/badge.svg)](https://github.com/DCKartasoft/Jupyter-Claude_Plugin/actions/workflows/build.yml)

A JupyterLab extension enabling collaborative development between users and Claude. Chat about your notebook, generate cells from prompts, explain and document existing code, and fix errors — all within JupyterLab.

> **Status:** early development, scaffold phase complete. See [docs/PLAN.md](docs/PLAN.md) for the implementation plan and [docs/DECISIONS.md](docs/DECISIONS.md) for the decision log.

## Features (v1)

- **Chat about the notebook** — ask Claude to analyze, summarize, or answer questions about your entire notebook
- **Generate a cell** — describe what you want, Claude generates working code and inserts it
- **Explain a cell** — Claude documents an existing cell with a markdown explanation
- **Fix last error** — Claude sees the error from your last cell run and offers a corrected version

## Requirements

- JupyterLab >= 4.0.0
- Node >= 20
- Python >= 3.10 (this project targets 3.13)
- `uv` package manager (via Homebrew: `brew install uv`)

## Development install

```bash
cd /path/to/Jupyter-Claude_Plugin
uv venv
source .venv/bin/activate

# Frontend deps
jlpm install

# Python deps (editable install)
uv pip install -e ".[dev,test]"
uv pip install jupyter-mcp-server jupyter-collaboration claude-agent-sdk

# Link the labextension into the running JupyterLab dev build
jupyter labextension develop . --overwrite
jupyter server extension enable jupyter_claude

# Start JupyterLab
jupyter lab
```

## Global MCP servers (user scope, one-time)

```bash
claude mcp add --scope user filesystem -- npx -y @modelcontextprotocol/server-filesystem $HOME
claude mcp add --scope user memory -- npx -y @modelcontextprotocol/server-memory
claude mcp add --scope user sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking
claude mcp add --scope user fetch -- uvx mcp-server-fetch
claude mcp add --scope user git -- uvx mcp-server-git
claude mcp add --scope user jupyter --transport http http://localhost:8888/mcp
```

## Backend

The extension supports two Claude backends. Pick one in the JupyterLab Settings Editor (or via `jupyter_server_config.py`) — everything else is derived from that choice.

### Anthropic direct

Set `ANTHROPIC_API_KEY` in the environment before launching Jupyter. The extension will use the `model` trait (default `claude-opus-4-8`).

### AWS Bedrock via shared SSO

Configuration lives in the extension traits (not shell env — the extension writes the right vars into the Claude Agent SDK subprocess itself):

- `backend = "bedrock"`
- `aws_region = "us-east-1"` (or your region)
- `aws_profile = "<your profile>"` — a named profile from `~/.aws/config`
- `default_opus_model`, `default_sonnet_model`, `default_haiku_model` — inference-profile IDs (defaults are set for the current Bedrock lineup: `us.anthropic.claude-opus-4-7`, `us.anthropic.claude-sonnet-4-6`, `us.anthropic.claude-haiku-4-5-20251001-v1:0`)

Refresh your SSO session and start Jupyter with `aws-vault` so the subprocess inherits temporary STS credentials without leaking them to disk:

```bash
aws sso login --profile <your profile>              # once per session
aws-vault exec <your profile> -- jupyter lab
```

If you prefer not to use `aws-vault`, `AWS_PROFILE=<name> AWS_REGION=<region> jupyter lab` also works — the extension forwards those to the SDK.

See [docs/PLAN.md](docs/PLAN.md) for design details.

## Architecture

```
JupyterLab (browser)
  └─ Frontend extension (TS/React)
       ├─ Right-side chat panel
       ├─ Cell toolbar buttons
       └─ Context-menu items
                          ↓ WebSocket
                  Server extension (Python)
                    └─ ClaudeSDKClient
                         ├─ Anthropic API | AWS Bedrock
                         └─ Jupyter MCP server (same process)
```

Claude reads/writes/executes cells via MCP tools; the extension provides no custom cell tools.

## Troubleshoot

If the frontend extension is not working, check that the server extension is enabled:

```bash
jupyter server extension list
```

If the server extension is installed and enabled but the frontend is not showing up, check that the frontend extension is installed:

```bash
jupyter labextension list
```

## Documentation

- [docs/PLAN.md](docs/PLAN.md) — step-by-step implementation roadmap
- [docs/DECISIONS.md](docs/DECISIONS.md) — decision log and rationale
- [docs/Architecture.md](docs/Architecture.md) — component diagram and data flow
- [CHANGELOG.md](CHANGELOG.md) — human-readable milestone log

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

_This README is maintained by an automated doc-keeper — it re-writes from [docs/DECISIONS.md](docs/DECISIONS.md) every 10 minutes._

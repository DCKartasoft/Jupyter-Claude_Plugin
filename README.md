# Jupyter Claude Plugin

A JupyterLab extension enabling collaborative development between users and Claude. Chat about your notebook, generate cells from prompts, explain and document existing code, and fix errors — all within JupyterLab.

> **Status:** early development, scaffold phase complete. See [docs/PLAN.md](docs/PLAN.md) for the implementation plan and [docs/DECISIONS.md](docs/DECISIONS.md) for the decision log.

![Jupyter Claude Plugin](Jupyter-%20Claude%20plugin.jpg)

## Features (v1)

- **Chat about the notebook** — ask Claude to analyze, summarize, or answer questions about your entire notebook
- **Generate a cell** — describe what you want; choose cell type (code/markdown/raw); Claude generates and inserts it
- **Explain a cell** — Claude documents an existing cell with a markdown explanation
- **Fix last error** — Claude sees the error from your last cell run and offers a corrected version
- **Runtime tier selector** — switch between opus/sonnet/haiku in the chat panel for quality/speed tradeoffs (Bedrock only)
- **MCP server management** — enable/disable individual MCP servers from `~/.claude.json` per session via dialog command (defaults to Jupyter only for faster startup)
- **Notebook toolbar buttons** — all five commands as icons in toolbar: Open Chat, Generate cell, Explain cell, Fix last error, and MCP server selector
- **Visual feedback** — animated "Claude is thinking…" spinner while processing; disabled tier selector during requests

## Requirements

- JupyterLab >= 4.0.0
- Node >= 20
- Python >= 3.10 (this project targets 3.13)
- `uv` package manager (via Homebrew: `brew install uv`)

## Install (from PyPI, recommended)

```bash
pip install --pre jupyter-claude-plugin
```

`--pre` is required for alpha releases (currently `0.1.0a1`). Runtime dependencies (`claude-agent-sdk`, `jupyter-mcp-server`, `jupyter-collaboration`) are pulled in automatically. See [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for backend configuration and usage.

## Development install (from source)

```bash
cd /path/to/Jupyter-Claude_Plugin
uv venv
source .venv/bin/activate

jlpm install
uv pip install -e ".[dev,test]"
jlpm build
jupyter labextension develop . --overwrite
jupyter server extension enable jupyter_claude

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

Set `ANTHROPIC_API_KEY` in the environment before launching Jupyter. The extension will use the `model` trait (default `claude-opus-latest`).

### AWS Bedrock via shared SSO

Configuration lives in the extension traits (not shell env — the extension writes the right vars into the Claude Agent SDK subprocess itself):

- `backend = "bedrock"`
- `aws_region = "us-east-1"` (or your region)
- `aws_profile = "<your profile>"` — a named profile from `~/.aws/config` (enables shared AWS SSO; profile and region are forwarded to the SDK subprocess)
- `default_fable_model`, `default_opus_model`, `default_sonnet_model`, `default_haiku_model` — inference-profile model IDs (defaults: `us.anthropic.claude-fable-5-1`, `us.anthropic.claude-opus-5-5`, `us.anthropic.claude-sonnet-5-5`, `us.anthropic.claude-haiku-5-5`)

Refresh your SSO session and start Jupyter with `aws-vault` so the subprocess inherits temporary STS credentials without leaking them to disk:

```bash
aws sso login --profile <your profile>              # once per session
aws-vault exec <your profile> -- jupyter lab
```

If you prefer not to use `aws-vault`, `AWS_PROFILE=<name> AWS_REGION=<region> jupyter lab` also works — the extension forwards those to the SDK.

### Per-machine model and region config (`jupyter_claude_models.json`)

To set the AWS region and model IDs for a machine without reinstalling the plugin or editing `jupyter_server_config.py`, create `~/.jupyter/jupyter_claude_models.json`. A ready-to-edit copy is at [examples/jupyter_claude_models.json](examples/jupyter_claude_models.json) (on GitHub, open it and use **Download raw file**):

```json
{
  "aws_region": "us-east-1",
  "direct": "claude-opus-latest",
  "fable": "us.anthropic.claude-fable-5-1",
  "opus": "us.anthropic.claude-opus-5-5",
  "sonnet": "us.anthropic.claude-sonnet-5-5",
  "haiku": "us.anthropic.claude-haiku-5-5"
}
```

| Key | Overrides | Used when |
|---|---|---|
| `aws_region` | `aws_region` | Bedrock backend |
| `direct` | `model` | Anthropic direct backend |
| `fable`, `opus`, `sonnet`, `haiku` | `default_<tier>_model` | Bedrock backend (inference-profile IDs) |

- All keys are optional; omitted keys fall back to the built-in defaults.
- Values in this file **take precedence** over the same settings in `jupyter_server_config.py`.
- The file is read at server startup — restart Jupyter after editing it.
- **Data sovereignty:** keep the region and the inference-profile prefix consistent (e.g. `eu-west-1` with `eu.anthropic...` IDs). The default `us.` profiles route across US regions. List the profiles available in your region with `aws bedrock list-inference-profiles --region <region>`.

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

- **[docs/USER_GUIDE.md](docs/USER_GUIDE.md) — install & operation guide (start here)**
- [docs/PLAN.md](docs/PLAN.md) — step-by-step implementation roadmap
- [docs/DECISIONS.md](docs/DECISIONS.md) — decision log and rationale
- [docs/Architecture.md](docs/Architecture.md) — component diagram and data flow
- [CHANGELOG.md](CHANGELOG.md) — human-readable milestone log

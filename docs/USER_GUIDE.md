# Jupyter Claude — User Guide

Install and use the Jupyter Claude extension in your own JupyterLab environment.

> This guide is for **using** the extension. To hack on the extension itself, see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Contents

- [What you get](#what-you-get)
- [Requirements](#requirements)
- [Install](#install)
- [Configure a backend](#configure-a-backend)
- [Launch JupyterLab](#launch-jupyterlab)
- [Using the extension](#using-the-extension)
- [Configuration reference](#configuration-reference)
- [Running on AWS SageMaker](#running-on-aws-sagemaker)
- [Troubleshooting](#troubleshooting)
- [Uninstall](#uninstall)

---

## What you get

- **Right-sidebar chat panel** — talk to Claude about the notebook you have open. Claude can read cells, insert new ones, and execute them for you.
- **Cell/notebook commands** available from the toolbar, right-click menu, and command palette (`⌘⇧C`):
  - **Open Claude Chat** — reveal the sidebar.
  - **Generate cell with Claude…** — pick `code` / `markdown` / `raw`, describe what you want, Claude inserts and (for code) executes it.
  - **Explain this cell with Claude** — inserts a markdown cell above the current one describing what the code does.
  - **Fix last error with Claude** — after a cell raises, Claude sees the traceback and inserts a corrected cell below.
  - **MCP servers…** — choose which MCP servers Claude is allowed to use (from your `~/.claude.json`).
- **Model tier selector** in the panel header — flip between Opus / Sonnet / Haiku mid-session. Sonnet is the default for speed; switch to Opus for harder reasoning.

## Requirements

- **JupyterLab ≥ 4.0** (extension is built for JupyterLab 4)
- **Python ≥ 3.10** (project uses 3.13; broader compat 3.10–3.14)
- **Node ≥ 20** — only required if you build from source; not needed if you install the built wheel
- One of:
  - **Anthropic API key** — set `ANTHROPIC_API_KEY` in your environment, or
  - **AWS Bedrock access** — an AWS profile with `bedrock:InvokeModel` permission for the three Claude inference profiles below

## Install

### Recommended: from PyPI

The extension is published to PyPI as `jupyter-claude-plugin`. Runtime dependencies (`claude-agent-sdk`, `jupyter-mcp-server`, `jupyter-collaboration`) are pulled in automatically.

Because the initial release is an alpha, you need `--pre` to install it:

```bash
pip install --pre jupyter-claude-plugin
```

Or with `uv`:

```bash
uv pip install --prerelease=allow jupyter-claude-plugin
```

Verify:

```bash
jupyter server extension list      # jupyter_claude, jupyter_mcp_server, jupyter_mcp_tools all "OK"
jupyter labextension list          # @dckartasoft/jupyter-claude enabled OK
```

### From source (for hacking on the extension)

Requires Node ≥ 20 for the frontend build. See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full dev workflow, or the short form:

```bash
git clone https://github.com/DCKartasoft/Jupyter-Claude_Plugin.git
cd Jupyter-Claude_Plugin

uv venv && source .venv/bin/activate
uv pip install -e ".[dev,test]"
jlpm install && jlpm build
jupyter labextension develop . --overwrite
jupyter server extension enable jupyter_claude
```

## Configure a backend

The extension needs to know how to reach Claude. Put your choice in `~/.jupyter/jupyter_server_config.py`. Create the file if it doesn't exist.

### Option A — Anthropic direct

```python
c = get_config()  # noqa
c.ClaudeExtensionApp.backend = "anthropic"
c.ClaudeExtensionApp.model = "claude-opus-4-8"   # or any Anthropic model id
c.ClaudeExtensionApp.permission_mode = "acceptEdits"
```

Then set `ANTHROPIC_API_KEY` in your shell before launching JupyterLab.

### Option B — AWS Bedrock via shared SSO (recommended for enterprise)

```python
c = get_config()  # noqa
c.ClaudeExtensionApp.backend = "bedrock"
c.ClaudeExtensionApp.aws_region = "us-east-1"
c.ClaudeExtensionApp.aws_profile = "<your-sso-profile-name>"

# These are the current defaults for Bedrock — override if your account has different profiles
c.ClaudeExtensionApp.default_opus_model = "us.anthropic.claude-opus-4-7"
c.ClaudeExtensionApp.default_sonnet_model = "us.anthropic.claude-sonnet-4-6"
c.ClaudeExtensionApp.default_haiku_model = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

c.ClaudeExtensionApp.permission_mode = "acceptEdits"
```

Refresh your SSO session before launching:

```bash
aws sso login --profile <your-sso-profile-name>
```

Test that Bedrock is actually reachable:

```bash
aws bedrock list-inference-profiles --profile <your-sso-profile-name> --region us-east-1 \
  | grep -E "opus|sonnet|haiku"
```

You should see the three profile IDs you configured above.

## Launch JupyterLab

```bash
source .venv/bin/activate
AWS_PROFILE=<your-sso-profile-name> AWS_REGION=us-east-1 jupyter lab
```

(For Anthropic direct, just `jupyter lab` after exporting `ANTHROPIC_API_KEY`.)

Open the URL Jupyter prints. Look for the **Claude icon** in the right sidebar. Click it to reveal the chat panel — the top line should read `Connected — bedrock / us.anthropic.claude-sonnet-4-6` (or the equivalent for your setup).

## Using the extension

### Chat about a notebook

Open a notebook, click the Claude tab in the right sidebar, and type a question. Claude has read access to the notebook via the Jupyter MCP tools — it can call `read_notebook`, `read_cell`, `list_notebooks`, etc.

Example prompts:

- *"What does this notebook do?"*
- *"The DataFrame in cell 3 has a weird schema — what's going on?"*
- *"Add a docstring to the function in the currently selected cell."*

### Generate a cell

**Command palette (`⌘⇧C`) → "Generate cell with Claude…"** or the ★ toolbar button on the notebook.

1. Pick the cell type — `code`, `markdown`, or `raw`.
2. Describe what you want (e.g. *"load iris.csv into a pandas DataFrame and show df.head()"*).
3. Claude inserts the cell into the current notebook. For `code` cells, it also executes them.

### Explain a cell

Right-click any code cell → **"Explain this cell with Claude"**. Claude inserts a markdown cell immediately above it describing what the code does.

### Fix the last error

Run a cell that raises (e.g. `1/0`). Then invoke **"Fix last error with Claude"** from the palette or the notebook toolbar. Claude sees the source of the failed cell, the exception name/value, and the traceback, and inserts a corrected version below.

If the command reports "No recent cell error captured", make sure you actually ran a cell that errored *in this notebook tab* — the tracker keys errors per notebook.

### Choose which MCP servers Claude may use

Palette → **"MCP servers…"** opens a dialog listing every MCP server registered at user scope in `~/.claude.json`. Check the ones Claude is allowed to invoke. `jupyter` is always required (it's how cells get read/written) and shown as locked.

Your selection persists across sessions.

### Model tier

Use the dropdown in the chat panel header (Opus / Sonnet / Haiku). Switching tears down the current Claude session and starts a fresh one with the new model — expect a moment of latency and a new `Connected — …` banner.

## Configuration reference

Every setting is a trait on `ClaudeExtensionApp` and configurable via `jupyter_server_config.py`, the JupyterLab Settings Editor, or a `--ClaudeExtensionApp.<name>=<value>` CLI flag.

| Trait | Type | Default | Notes |
|---|---|---|---|
| `backend` | `"anthropic"` \| `"bedrock"` | `"anthropic"` | Which API to talk to |
| `model` | str | `"claude-opus-4-8"` | Anthropic-direct only; unused for Bedrock |
| `aws_region` | str | `"us-east-1"` | Bedrock region |
| `aws_profile` | str | `""` | Named profile from `~/.aws/config`; empty = use process env |
| `default_opus_model` | str | `"us.anthropic.claude-opus-4-7"` | Bedrock inference profile |
| `default_sonnet_model` | str | `"us.anthropic.claude-sonnet-4-6"` | Bedrock inference profile |
| `default_haiku_model` | str | `"us.anthropic.claude-haiku-4-5-20251001-v1:0"` | Bedrock inference profile |
| `main_model_tier` | `"opus"` \| `"sonnet"` \| `"haiku"` | `"sonnet"` | Default tier when the panel first opens |
| `system_prompt` | str | see `config.py` | Prepended to every conversation |
| `permission_mode` | `"default"` \| `"acceptEdits"` \| `"plan"` \| `"bypassPermissions"` | `"default"` | `acceptEdits` skips confirmation dialogs when Claude uses MCP tools; `bypassPermissions` is dangerous |
| `enabled_mcp_servers` | list[str] | `["jupyter"]` | Which MCP servers Claude may call. `jupyter` is always forced-included |
| `jupyter_mcp_url` | str | `""` | Empty = auto-detect from Jupyter's port |
| `verbose` | bool | `False` | Log every SDK message at INFO |

## Running on AWS SageMaker

The extension is a standard pip-installable JupyterLab 4 extension, so it runs on any SageMaker environment that ships JupyterLab 4. Bedrock is the natural backend choice — the IAM role attached to the SageMaker environment supplies credentials automatically, so `aws_profile` stays empty.

### Which SageMaker environment?

| Environment | JupyterLab version | Verdict |
|---|---|---|
| **SageMaker Studio (JupyterLab 4)** | 4.x | Supported — best fit. |
| SageMaker Studio Classic | 3.x | Not supported without a JupyterLab-3 port; we pin to JupyterLab 4 APIs. |
| SageMaker Notebook Instances | Varies by AMI (often 3.x) | Check `jupyter lab --version`. If < 4, upgrade the environment or skip. |

Run `jupyter lab --version` in a terminal inside your SageMaker space to confirm.

### IAM permissions

Attach an inline policy to the execution role used by your SageMaker space:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListInferenceProfiles",
        "bedrock:GetInferenceProfile"
      ],
      "Resource": "*"
    }
  ]
}
```

Confirm access from a terminal inside the space:

```bash
aws bedrock list-inference-profiles --region us-east-1 | grep -E "opus|sonnet|haiku"
```

### Setup script

Save this as a **SageMaker Studio lifecycle configuration** (recommended, so it re-runs on space restart) or paste it into a terminal for a one-off install:

```bash
#!/bin/bash
set -euo pipefail

# --- Node + Claude Code CLI (needed by claude-agent-sdk) ---
if ! command -v node >/dev/null || [ "$(node --version | cut -d. -f1 | tr -d v)" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
sudo npm install -g @anthropic-ai/claude-code

# --- Extension (from PyPI; pulls in claude-agent-sdk, jupyter-mcp-server, jupyter-collaboration) ---
pip install --pre jupyter-claude-plugin

# --- Server config: use IAM role, not a named profile ---
mkdir -p ~/.jupyter
cat > ~/.jupyter/jupyter_server_config.py <<'EOF'
c = get_config()  # noqa
c.ClaudeExtensionApp.backend = "bedrock"
c.ClaudeExtensionApp.aws_region = "us-east-1"
c.ClaudeExtensionApp.aws_profile = ""   # empty → use the notebook IAM role
c.ClaudeExtensionApp.permission_mode = "acceptEdits"
EOF

# --- Restart Jupyter Server so the config takes effect ---
# In Studio: File → Shut Down, then relaunch the space.
```

### SageMaker-specific gotchas

- **`aws_profile` must be empty.** Named profiles look up `~/.aws/credentials`, which the SageMaker execution role doesn't populate. Leave the trait blank so the standard AWS credential chain finds the instance metadata.
- **`~/.claude.json` won't exist** on a fresh space, so the "MCP servers…" picker shows only `jupyter`. That's fine — Jupyter MCP is all you need for cell R/W/execute. If you want additional MCP servers, run `claude mcp add --scope user <name> -- <cmd>` inside the space.
- **Studio environments are ephemeral.** Pip installs into the space's Python env don't survive restarts unless persisted. Put the `pip install --pre jupyter-claude-plugin` line in a lifecycle configuration so it re-runs on each space startup, or bake the extension into a custom Studio image for zero-latency startup.
- **Bedrock model IDs are region-specific.** The defaults in `config.py` target `us-east-1`. In other regions, look up the correct inference-profile IDs with `aws bedrock list-inference-profiles --region <your-region>` and override the three `default_*_model` traits.
- **Egress:** Bedrock is reached via AWS-internal endpoints, so no VPC egress rules to loosen. This is one advantage over Anthropic direct on SageMaker.

## Troubleshooting

### The Claude tab doesn't appear in the sidebar

1. **Confirm the extension is installed AND enabled:**
   ```bash
   jupyter labextension list | grep claude   # should show "enabled OK"
   ```
2. **Check for stale `disabledExtensions` / `lockedExtensions`:**
   ```bash
   find "$(python -c 'import sys; print(sys.prefix)')/etc/jupyter/labconfig" -name page_config.json
   ```
   Open the file and confirm `dckartasoft-jupyter-claude` is NOT in either list. If it is, remove it and restart JupyterLab.
3. **Open the browser DevTools console** and look for `JupyterLab extension @dckartasoft/jupyter-claude is activated!`. If that line is missing, the plugin isn't running — usually a dependency-injection failure. Check the console for red errors.

### "Connected — bedrock / …" never appears

Server-side WebSocket issue. Check:

```bash
tail -f /path/to/jupyter.log     # or the terminal where you launched jupyter lab
```

Common causes:

- **SSO token expired** — re-run `aws sso login --profile <name>`.
- **Wrong region** — inference profiles are region-specific. `us-east-1` is the safe default.
- **IAM missing `bedrock:InvokeModel`** — check with `aws sts get-caller-identity --profile <name>` and confirm the role.
- **Model ID typo** — Opus/Sonnet omit the version-date suffix; Haiku includes `-20251001-v1:0`. Don't "normalize" them.

### Chat sends but no response comes back

- Check the JupyterLab terminal log for stack traces from the Claude Agent SDK.
- Confirm `jupyter_mcp_server` is loaded: `jupyter server extension list | grep mcp`.
- The extension needs `jupyter-collaboration` for MCP cell reads to work — verify it's installed.

### Cells insert but never execute

The generate/fix commands call `mcp__jupyter__insert_execute_code_cell`, which requires a **running kernel** in the notebook. If your kernel is dead or not started, the cell is inserted but stays unexecuted. Start/restart the kernel and try again.

### Extension is enabled but ignored by JupyterLab after a `pip install` update

Rebuild the labextension link:

```bash
jupyter labextension develop . --overwrite
```

Then hard-refresh the browser (`⌘⇧R`).

## Uninstall

```bash
jupyter server extension disable jupyter_claude
jupyter labextension uninstall @dckartasoft/jupyter-claude   # if installed from a wheel
uv pip uninstall jupyter_claude
```

If you installed with `jupyter labextension develop . --overwrite` (source install), remove the symlink JupyterLab created:

```bash
jupyter labextension list                    # find the labextensions path
rm "$(python -c 'import sys; print(sys.prefix)')/share/jupyter/labextensions/@dckartasoft/jupyter-claude"
```

## Related docs

- [README.md](../README.md) — project overview
- [CONTRIBUTING.md](../CONTRIBUTING.md) — dev workflow, build, tests
- [docs/Architecture.md](Architecture.md) — component diagram, data flow
- [docs/PLAN.md](PLAN.md) — full implementation plan
- [docs/DECISIONS.md](DECISIONS.md) — decision journal

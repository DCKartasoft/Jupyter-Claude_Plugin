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

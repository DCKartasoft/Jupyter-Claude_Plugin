# jupyter-claude-plugin — Current State

> Deployment and operations reference. Updated as significant changes land.
> Last updated: 2026-08-17

---

## Release

**PyPI:** `jupyter-claude-plugin 0.1.0a1` — live. Install verified:
```bash
uv pip install --pre jupyter-claude-plugin
# → @dckartasoft/jupyter-claude v0.1.0-alpha.1 enabled OK
```

**CI:** Green on all four workflows (build, Check Links, Integration tests, test_isolated).

**Branch:** `main` — all work pushed to `origin/main`.

---

## Recent Commits

```
b549ed4  ci: retrigger build
e9196ad  style: fix Prettier formatting in README
18ad0ce  docs: add plugin screenshot to README
cdfeeaa  build: exclude .claude/ directory from git tracking
52c69fe  perf: local notebook snapshot + restrained system prompt
0a37a7a  feat: notebook-aware prompts, custom SVG icons, multi-line generate dialog
10ab81c  docs: correct doc-keeper cadence — hourly, not every 10 minutes
f225cbb  build: exclude .claude/ from sdist
215d63c  ci: remove GitHub Actions badge from README (404s on private repo)
3e6c3c6  ci: fix Playwright activation test + broaden check-links ignore
```

---

## Config Surface

All traits are set in `~/.jupyter/jupyter_server_config.py` or JupyterLab Settings Editor.

| Trait | Type | Default | Notes |
|---|---|---|---|
| `backend` | enum | `anthropic` | `anthropic` or `bedrock` |
| `model` | str | `claude-opus-4-8` | Anthropic-direct only |
| `aws_region` | str | `us-east-1` | Bedrock region |
| `aws_profile` | str | `""` | SSO profile; leave empty on SageMaker (uses IMDS) |
| `default_opus_model` | str | `us.anthropic.claude-opus-4-7` | Bedrock inference profile ID |
| `default_sonnet_model` | str | `us.anthropic.claude-sonnet-4-6` | Bedrock inference profile ID |
| `default_haiku_model` | str | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Bedrock inference profile ID |
| `main_model_tier` | enum | `sonnet` | opus / sonnet / haiku |
| `system_prompt` | str | (see config.py) | Steers Claude toward notebook snapshot |
| `notebook_snapshot_max_cells` | int | `50` | Cells included in prompt prefix |
| `notebook_snapshot_max_source_chars` | int | `2000` | Per-cell char cap |
| `jupyter_mcp_url` | str | `""` | Auto-detected from Jupyter port when empty |
| `enabled_mcp_servers` | list | `["jupyter"]` | `jupyter` always force-added |
| `permission_mode` | enum | `default` | `acceptEdits` recommended |
| `verbose` | bool | `False` | Logs every SDK message at INFO |
| `cloudwatch_log_group` | str | `""` | CW log group for per-user tracking; disabled when empty |
| `cloudwatch_region` | str | `""` | CW client region; falls back to `aws_region` when empty |

---

## Local Dev Config (`~/.jupyter/jupyter_server_config.py`)

```python
c = get_config()
c.ClaudeExtensionApp.backend = "bedrock"
c.ClaudeExtensionApp.aws_region = "us-east-1"
c.ClaudeExtensionApp.aws_profile = "bedrock-claude"
c.ClaudeExtensionApp.default_opus_model = "us.anthropic.claude-opus-4-7"
c.ClaudeExtensionApp.default_sonnet_model = "us.anthropic.claude-sonnet-4-6"
c.ClaudeExtensionApp.default_haiku_model = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
c.ClaudeExtensionApp.permission_mode = "acceptEdits"
c.ClaudeExtensionApp.verbose = True
```

Launch: `aws-vault exec bedrock-claude -- jupyter lab`
Fallback: `AWS_PROFILE=bedrock-claude AWS_REGION=us-east-1 jupyter lab`
Log: `/tmp/jupyter-claude.log`

---

## SageMaker Config (`~/.jupyter/jupyter_server_config.py` on instance)

```python
c = get_config()
c.ClaudeExtensionApp.backend = "bedrock"
c.ClaudeExtensionApp.aws_region = "us-east-2"          # Bedrock governance region
# NO aws_profile — SageMaker execution role provides credentials via IMDS
c.ClaudeExtensionApp.default_opus_model = "us.anthropic.claude-opus-4-7"
c.ClaudeExtensionApp.default_sonnet_model = "us.anthropic.claude-sonnet-4-6"
c.ClaudeExtensionApp.default_haiku_model = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
c.ClaudeExtensionApp.permission_mode = "acceptEdits"
c.ClaudeExtensionApp.cloudwatch_log_group = "/aws/jupyter-claude/sessions-dev"
c.ClaudeExtensionApp.cloudwatch_region = "us-east-1"   # SageMaker instance region
```

Launch: `jupyter lab` — no aws-vault or profile needed.

**Prerequisites (infrastructure not yet deployed):**
- `Claude_Bedrock_CLI` stacks `dev/use1/07-jupyter-claude-logging` and `08-sagemaker-execution-role` must be deployed first.
- See `Claude_Bedrock_CLI/Docs/SAGEMAKER-JUPYTER-INTEGRATION.md` for full instructions.

---

## Uncommitted Changes (2026-08-17)

| File | Change |
|---|---|
| `jupyter_claude/config.py` | Added `cloudwatch_log_group` and `cloudwatch_region` traits |
| `jupyter_claude/chat_handler.py` | CloudWatch per-user session logging on `ResultMessage` |

Hold for commit until SageMaker infrastructure is deployed and testable.

---

## Known Sharp Edges

- **Node missing:** If `jlpm build` silently fails, check `node --version`. Node was accidentally uninstalled once (2026-07-14); reinstall with `brew install node`.
- **No `npm run dev`:** This project uses `jlpm`, not `npm`. Dev build: `jlpm watch`. The test interface is `jupyter lab` itself.
- **Stale labextension bundle:** If the browser loads old code after a `jlpm build`, run `jupyter labextension develop . --overwrite` to restore the symlink.
- **Silent plugin disable:** `.venv/etc/jupyter/labconfig/page_config.json` can silently disable the extension. Should be `{"disabledExtensions": {}, "lockedExtensions": {}}`.
- **`scheduled_tasks.json` noise:** Always appears in `git status` (cron timestamp updates). Stage specific files only — never `git add .`.

---

## What's Next

1. **In progress:** Deploy SageMaker infrastructure in `Claude_Bedrock_CLI`
2. Commit CloudWatch plugin changes once infra is ready to test
3. Optional: tag `v0.1.0a1` on GitHub
4. Optional: wire GitHub Actions trusted publishing (`publish-release.yml`)
5. Deferred: `stream_cell_delta` tool for token-by-token cell fill-in

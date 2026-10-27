# Jupyter Claude Plugin — SageMaker Notebook Setup Guide

> This guide covers the **isolated MCP server architecture** required for SageMaker notebook
> instances (classic, AL2023). This approach was confirmed working 2026-09-02 following an
> AWS Support recommendation to isolate the collaboration stack.
>
> For local dev setup, see [USER_GUIDE.md](USER_GUIDE.md).

## Architecture Overview

```
JupyterSystemEnv (port 8443, primary server)
  └── jupyter-claude-plugin (no collaboration stack)
        └── connects via HTTP → http://127.0.0.1:8889/mcp

SageMaker/mcp-isolated-env (port 8889, loopback only)
  └── jupyter-mcp-server only
        └── All Jupyter dirs under SageMaker/ (persist across Stop/Start)
```

**Why isolated?** `jupyter-mcp-server` depends on `jupyter-server-nbmodel` (Datalayer), which
ships a frontend labextension that intercepts notebook opens and fails with
`{"reason":"unknown_session"}` on SageMaker's auth proxy — causing permanent spinners and
"session expired" dialogs. Running the MCP server in a completely separate venv with its own
Jupyter dirs keeps JupyterSystemEnv clean.

---

## Contents

- [Prerequisites](#prerequisites)
- [Automated lifecycle setup (recommended)](#automated-lifecycle-setup)
- [Manual setup](#manual-setup)
- [Manual MCP server restart (after primary server restart)](#manual-mcp-server-restart)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

1. **SageMaker execution role** must have:
   - `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` on Claude inference profiles
   - `logs:CreateLogStream` and `logs:PutLogEvents` on `/aws/jupyter-claude/sessions`
   - `ssm:PutParameter` on `/jupyter-claude-federated/*`
   - Provisioned by the `dev-sagemaker-execution-role` CloudFormation stack in `Claude_Bedrock_CLI`

2. **Instance type**: `ml.t3.medium` or larger. The lifecycle script skips validation on `ml.t3.*` instances.

3. **Python 3.10** available in JupyterSystemEnv (`/home/ec2-user/anaconda3/envs/JupyterSystemEnv`). Required for `mcp[cli]` dependency.

---

## Automated Lifecycle Setup

The preferred approach. The lifecycle block is in `Jupyter-Claude-Federated/sagemaker/on_start_federated.sh` and is sourced from the main `on_start.sh` in the `iac_deployment` repo.

**Deploy via Sceptre** (from `iac_deployment/`):
```bash
sceptre --var-file config/vars/dev.yaml launch dev/use2/Assets/dcdevmlps-v0/mlps-al2023-deploy
```

The lifecycle script performs 11 steps (fully backgrounded, never blocks the 5-min timeout):

| Step | Action |
|------|--------|
| 1 | Remove collaboration stack from JupyterSystemEnv |
| 2 | Restart primary server (clean state) |
| 3 | Create isolated venv at `SageMaker/mcp-isolated-env` using JupyterSystemEnv Python 3.10 |
| 4 | Install `jupyter-mcp-server>=0.1.0` in isolated venv (idempotent) |
| 5 | Generate/read stable token at `SageMaker/mcp-isolated-token` |
| 6 | Publish token to SSM (`/jupyter-claude-federated/{instance}/token`) |
| 7 | Kill any stale MCP server process |
| 8 | Install `claude-agent-sdk>=0.1` (--pre), then `jupyter-claude-plugin>=0.1.0a5` |
| 9 | Write `jupyter_server_config.py` (idempotent `[jcf-begin]/[jcf-end]` block) |
| 10 | Restart primary server to load the plugin |
| 11 | **Start isolated MCP server** (after all restarts — won't be killed) |

Log: `~/SageMaker/logs/jupyter-mcp.log`

---

## Manual Setup

If the lifecycle script hasn't run or you need to bootstrap manually:

### 1. Remove collaboration stack from JupyterSystemEnv

```bash
JUPYTER_ENV=/home/ec2-user/anaconda3/envs/JupyterSystemEnv
$JUPYTER_ENV/bin/pip uninstall -y \
  jupyter-mcp-server jupyter-collaboration jupyter-collaboration-ui \
  jupyter-docprovider jupyter-server-ydoc jupyter-server-nbmodel jupyter-server-fileid \
  2>/dev/null || true
```

### 2. Create isolated venv (if not already present)

```bash
$JUPYTER_ENV/bin/python -m venv /home/ec2-user/SageMaker/mcp-isolated-env
/home/ec2-user/SageMaker/mcp-isolated-env/bin/pip install "jupyter-mcp-server>=0.1.0"
```

### 3. Generate token

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))' \
  > /home/ec2-user/SageMaker/mcp-isolated-token
chmod 600 /home/ec2-user/SageMaker/mcp-isolated-token
```

### 4. Install plugin in JupyterSystemEnv

```bash
JUPYTER_ENV=/home/ec2-user/anaconda3/envs/JupyterSystemEnv
$JUPYTER_ENV/bin/pip install --pre "claude-agent-sdk>=0.1"
$JUPYTER_ENV/bin/pip install --pre "jupyter-claude-plugin>=0.1.0a5"
```

### 5. Write plugin config

```bash
MCP_TOKEN=$(cat /home/ec2-user/SageMaker/mcp-isolated-token)
cat >> ~/.jupyter/jupyter_server_config.py << PYEOF
# [jcf-begin]
import os as _os
_jcf_token_file = '/home/ec2-user/SageMaker/mcp-isolated-token'
_jcf_token = open(_jcf_token_file).read().strip() if _os.path.exists(_jcf_token_file) else ''
c.ClaudeExtensionApp.backend = 'bedrock'
c.ClaudeExtensionApp.aws_region = 'us-east-2'
c.ClaudeExtensionApp.jupyter_mcp_url = 'http://127.0.0.1:8889/mcp'
c.ClaudeExtensionApp.jupyter_mcp_token = _jcf_token
c.ClaudeExtensionApp.permission_mode = 'bypassPermissions'
c.ClaudeExtensionApp.cloudwatch_log_group = '/aws/jupyter-claude/sessions'
# [jcf-end]
PYEOF
```

**Note on region-specific model IDs:** If your Bedrock region uses different inference-profile IDs than the defaults (Claude 5 family in `us-east-1`), create `~/.jupyter/jupyter_claude_models.json` instead of modifying `jupyter_server_config.py` traits. Look up your region's profiles with `aws bedrock list-inference-profiles --region <your-region>` and set them in the JSON file — this persists across plugin updates without reinstalling.

### 6. Restart primary server

```bash
sudo systemctl restart jupyter-server
sleep 8
```

### 7. Start isolated MCP server

```bash
# Fix permissions first (if dirs were created as root)
sudo chown -R ec2-user:ec2-user \
  /home/ec2-user/SageMaker/mcp-isolated-jupyter-config \
  /home/ec2-user/SageMaker/mcp-isolated-jupyter-data \
  /home/ec2-user/SageMaker/mcp-isolated-jupyter-runtime \
  /home/ec2-user/SageMaker/logs/jupyter-mcp.log 2>/dev/null || true

MCP_TOKEN=$(cat ~/SageMaker/mcp-isolated-token)
mkdir -p ~/SageMaker/mcp-isolated-jupyter-{config,data,runtime} ~/SageMaker/logs
JUPYTER_CONFIG_DIR=/home/ec2-user/SageMaker/mcp-isolated-jupyter-config \
JUPYTER_DATA_DIR=/home/ec2-user/SageMaker/mcp-isolated-jupyter-data \
JUPYTER_RUNTIME_DIR=/home/ec2-user/SageMaker/mcp-isolated-jupyter-runtime \
nohup /home/ec2-user/SageMaker/mcp-isolated-env/bin/jupyter server \
  --ServerApp.ip=127.0.0.1 \
  --ServerApp.port=8889 \
  --IdentityProvider.token="$MCP_TOKEN" \
  --ServerApp.password='' \
  --ServerApp.disable_check_xsrf=True \
  --ServerApp.open_browser=False \
  --ServerApp.root_dir=/home/ec2-user/SageMaker \
  --ServerApp.kernel_spec_manager_class=jupyter_client.kernelspec.KernelSpecManager \
  >> ~/SageMaker/logs/jupyter-mcp.log 2>&1 &

sleep 3
# Verify it's up
curl -s "http://127.0.0.1:8889/mcp/healthz" \
  -H "Authorization: token $(cat ~/SageMaker/mcp-isolated-token)"
# Expected: {"status":"healthy",...}
```

---

## Manual MCP Server Restart

After any `systemctl restart jupyter-server` (which kills the MCP server), restart the MCP server:

```bash
# Kill stale process if any
pkill -u ec2-user -f "jupyter.*8889" 2>/dev/null || true
sleep 2

MCP_TOKEN=$(cat ~/SageMaker/mcp-isolated-token)
JUPYTER_CONFIG_DIR=/home/ec2-user/SageMaker/mcp-isolated-jupyter-config \
JUPYTER_DATA_DIR=/home/ec2-user/SageMaker/mcp-isolated-jupyter-data \
JUPYTER_RUNTIME_DIR=/home/ec2-user/SageMaker/mcp-isolated-jupyter-runtime \
nohup /home/ec2-user/SageMaker/mcp-isolated-env/bin/jupyter server \
  --ServerApp.ip=127.0.0.1 \
  --ServerApp.port=8889 \
  --IdentityProvider.token="$MCP_TOKEN" \
  --ServerApp.password='' \
  --ServerApp.disable_check_xsrf=True \
  --ServerApp.open_browser=False \
  --ServerApp.root_dir=/home/ec2-user/SageMaker \
  --ServerApp.kernel_spec_manager_class=jupyter_client.kernelspec.KernelSpecManager \
  >> ~/SageMaker/logs/jupyter-mcp.log 2>&1 &

sleep 3
ss -tlnp | grep 8889
# Expected: LISTEN 0 128 127.0.0.1:8889 ...
```

Then open a **new chat session** in the plugin (old sessions cached the failed connection).

---

## Troubleshooting

### `/mcp` returns 404 even though extension is listed as enabled

**Cause**: `JUPYTER_NO_CONFIG=1` was used (suppresses runtime Tornado handler registration even though static `extension list` still shows enabled). Or the extension is not loading.

**Fix**: Do NOT use `JUPYTER_NO_CONFIG=1`. Instead use `--ServerApp.kernel_spec_manager_class=jupyter_client.kernelspec.KernelSpecManager` to override the environment_kernels conflict.

**Verify**: `curl -s http://127.0.0.1:8889/mcp/healthz -H "Authorization: token $(cat ~/SageMaker/mcp-isolated-token)"` should return JSON.

---

### Auth fails (302 HTML redirect instead of JSON)

**Cause**: Using deprecated `--ServerApp.token` flag. Jupyter Server 2.x ignores it and uses a random token.

**Fix**: Use `--IdentityProvider.token="$MCP_TOKEN"` instead.

---

### MCP server crashes silently after start

**Cause 1**: Runtime dirs owned by root — ec2-user can't write cookie secret.
```bash
sudo chown -R ec2-user:ec2-user \
  ~/SageMaker/mcp-isolated-jupyter-{config,data,runtime} \
  ~/SageMaker/logs/jupyter-mcp.log
```

**Cause 2**: `environment_kernels.EnvironmentKernelSpecManager` error — system `/etc/jupyter/` config references a package not in isolated venv.
Fix: add `--ServerApp.kernel_spec_manager_class=jupyter_client.kernelspec.KernelSpecManager` to the server start command.

---

### Permission prompt appears when inserting cells

**Cause**: `permission_mode = 'acceptEdits'` — this only auto-approves built-in file writes. MCP tool calls still prompt.

**Fix**: Change to `permission_mode = 'bypassPermissions'` in `jupyter_server_config.py`, then restart primary server and MCP server.

---

### MCP server not running after Stop/Start

**Cause**: Lifecycle script started MCP server before the final `systemctl restart`, which killed it.

**Fix**: Latest `on_start_federated.sh` (step 11) starts the server AFTER all restarts. If running an older version, re-sync from S3 or redeploy via Sceptre.

---

### `mcp[cli]` no matching distribution

**Cause**: Isolated venv was created with system Python (too old). Must use JupyterSystemEnv Python 3.10.

**Fix**: Delete and recreate the venv:
```bash
rm -rf ~/SageMaker/mcp-isolated-env
/home/ec2-user/anaconda3/envs/JupyterSystemEnv/bin/python -m venv ~/SageMaker/mcp-isolated-env
~/SageMaker/mcp-isolated-env/bin/pip install "jupyter-mcp-server>=0.1.0"
```

---

## Related Docs

- [USER_GUIDE.md](USER_GUIDE.md) — general install and usage (local dev)
- `Jupyter-Claude-Federated/sagemaker/on_start_federated.sh` — authoritative lifecycle script
- `iac_deployment/.../dcdevmlps-v0/Scripts/on_start.sh` — main lifecycle that sources the above
- `docs/AWS-SUPPORT-INVESTIGATION.md` — original investigation that led to this architecture

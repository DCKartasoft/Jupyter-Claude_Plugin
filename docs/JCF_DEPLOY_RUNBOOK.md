# JCF Isolated MCP Deploy — Working Runbook

> Temporary doc. Captures every issue hit during the 2026-09-02 dcdevmlps-v0 deployment
> and the exact fix for each. Use this during test environment bring-up to cut diagnosis time.

---

## What "working" looks like

After lifecycle completes and JupyterLab loads:

```bash
# MCP server is up
ss -tlnp | grep 8889
# → LISTEN 0 128 127.0.0.1:8889 ... ("jupyter-server",pid=...,fd=...)

# Auth works
curl -s http://127.0.0.1:8889/api/kernels \
  -H "Authorization: token $(cat ~/SageMaker/mcp-isolated-token)"
# → []

# Extension is loaded and healthy
curl -s http://127.0.0.1:8889/mcp/healthz \
  -H "Authorization: token $(cat ~/SageMaker/mcp-isolated-token)"
# → {"status":"healthy","context_type":"JUPYTER_SERVER",...}
```

In JupyterLab: open a new chat session in the Claude panel → ask "insert a cell with 10*10" → cell inserted without any permission dialog.

---

## Lifecycle log location

```bash
tail -f ~/SageMaker/logs/jupyter-mcp.log
```

Healthy end state:
```
[jcf] ── on_start_federated begin ...
[jcf] Token published to SSM.
[jcf] jupyter-claude-plugin installed.
[jcf] Plugin config written to /home/ec2-user/.jupyter/jupyter_server_config.py
[jcf] Isolated MCP server started on 127.0.0.1:8889
[jcf] ── on_start_federated complete ...
```

---

## Issues hit — in order — with exact fixes

---

### 1. Lifecycle still shows old stale comment in AWS console

**Symptom**: Console shows `# Jupyter-Claude-Federated: headless MCP server...` after S3 upload.

**Cause**: S3 upload doesn't update the CloudFormation lifecycle config. The console shows the CFN-embedded script, not the S3 copy.

**Fix**: Sceptre redeploy:
```bash
cd ~/Dev/iac_deployment
sceptre --var-file config/vars/dev.yaml launch dev/use2/Assets/dcdevmlps-v0/mlps-al2023-deploy
```

---

### 2. `jupyter-mcp-server>=1.0` not found on PyPI

**Symptom**:
```
ERROR: Could not find a version that satisfies the requirement jupyter-mcp-server>=1.0
(from versions: 0.1.0)
```

**Cause**: Version constraint too strict — only `0.1.0` existed at that time (2.x was published later).

**Fix**: Change constraint to `>=0.1.0` in `on_start_federated.sh` step 4 pip install.

---

### 3. `mcp[cli]` no matching distribution

**Symptom**:
```
ERROR: Could not find a version that satisfies the requirement mcp[cli]
```

**Cause**: Isolated venv was created with system `python3` (Python 3.8 or older). `mcp[cli]` requires Python 3.10+.

**Fix**: Create isolated venv using JupyterSystemEnv Python explicitly:
```bash
/home/ec2-user/anaconda3/envs/JupyterSystemEnv/bin/python -m venv ~/SageMaker/mcp-isolated-env
```

The lifecycle script now checks and recreates the venv if the Python executable doesn't match.

---

### 4. `ModuleNotFoundError: No module named 'claude_agent_sdk'`

**Symptom**: Plugin fails to load with:
```
[W] extension failed loading: ModuleNotFoundError('No module named 'claude_agent_sdk'')
```

**Cause**: `claude-agent-sdk` is a pre-release package. `pip install jupyter-claude-plugin` doesn't auto-resolve pre-release transitive deps.

**Fix**: Install it explicitly with `--pre` before the plugin:
```bash
$PIP install --pre "claude-agent-sdk>=0.1"
$PIP install --pre "jupyter-claude-plugin>=0.1.0a5"
```

---

### 5. MCP server killed by `systemctl restart jupyter-server`

**Symptom**: MCP server starts in step 7, but after step 10 (`systemctl restart`) it's gone:
```bash
ps aux | grep "mcp-isolated-env"  # empty
ss -tlnp | grep 8889              # empty
```

**Cause**: `systemctl restart jupyter-server` kills all child/orphan processes started in the lifecycle. MCP server was started before the final restart.

**Fix**: Move MCP server start to **step 11** — after ALL `systemctl restart` calls. Add `sleep 5` after the step 10 restart to let the server fully come up before starting the MCP server.

---

### 6. Instance type check using IMDS fails

**Symptom**: Validation still runs on `ml.t3.medium` instances.

**Cause**: `curl http://169.254.169.254/.../instance-type` returns the instance type in a different format or times out on some SageMaker configs.

**Fix**: Use the SageMaker metadata file instead:
```bash
INSTANCE_TYPE=$(jq -r .InstanceType /opt/ml/metadata/resource-metadata.json 2>/dev/null || echo "unknown")
if [[ "$INSTANCE_TYPE" == *"ml.t3."* ]]; then
```

---

### 7. Log file owned by root — ec2-user can't write

**Symptom**: MCP server start fails with:
```
sh: /home/ec2-user/SageMaker/logs/jupyter-mcp.log: Permission denied
```

**Cause**: Lifecycle runs as root. `mkdir` + initial log write creates root-owned files. ec2-user can't append to the log.

**Fix**: Add to lifecycle immediately after mkdir:
```bash
touch "$LOG"
chown ec2-user:ec2-user "$LOG" "$MCP_CONFIG_DIR" "$MCP_DATA_DIR" "$MCP_RUNTIME_DIR" "$(dirname "$LOG")"
```

---

### 8. `environment_kernels.EnvironmentKernelSpecManager` crash

**Symptom**: MCP server crashes immediately on startup:
```
Bad config encountered during initialization: The 'kernel_spec_manager_class' trait ...
'environment_kernels.EnvironmentKernelSpecManager' could not be imported
```

**Cause**: System `/etc/jupyter/` config sets `kernel_spec_manager_class` to a package only installed in JupyterSystemEnv, not the isolated venv.

**Fix (attempted — WRONG)**: `JUPYTER_NO_CONFIG=1` — suppressed the crash but broke handler registration (see issue 10 below).

**Fix (correct)**: Override on the CLI — CLI args take precedence over config files:
```bash
--ServerApp.kernel_spec_manager_class=jupyter_client.kernelspec.KernelSpecManager
```

---

### 9. Runtime dirs owned by root — MCP server crashes after starting

**Symptom**: Server starts (logs `Jupyter Server ... is running at http://127.0.0.1:8889`) then immediately crashes:
```
PermissionError: [Errno 13] Permission denied: '...jupyter_cookie_secret'
PermissionError: [Errno 13] Permission denied: '.../jpserver-XXXXX-open.html'
```

**Cause**: `mcp-isolated-jupyter-runtime/` created by lifecycle (running as root). ec2-user can't write cookie secret or browser open file.

**Fix**:
```bash
sudo chown -R ec2-user:ec2-user \
  ~/SageMaker/mcp-isolated-jupyter-config \
  ~/SageMaker/mcp-isolated-jupyter-data \
  ~/SageMaker/mcp-isolated-jupyter-runtime
```

Lifecycle now does this automatically via the chown in step 0.

---

### 10. `/mcp` endpoint returns 404 even though extension is listed as enabled

**Symptom**:
```
curl http://127.0.0.1:8889/mcp → 404 Not Found (HTML)
curl http://127.0.0.1:8889/mcp/healthz → 404
```

`curl http://127.0.0.1:8889/mcp/` → 302 redirect to `/mcp` → 404 (circular).

`jupyter server extension list` shows `jupyter_mcp_server 2.1.3 OK`.

**Cause**: `JUPYTER_NO_CONFIG=1` was used to fix issue 8, but it suppresses the Tornado handler registration at runtime. The static extension list reads from venv config files (not suppressed), but the running server never wires up the `/mcp` routes.

**Fix**: Remove `JUPYTER_NO_CONFIG=1`. Use `--ServerApp.kernel_spec_manager_class=...` CLI arg instead (issue 8's correct fix). Routes register properly.

---

### 11. `--ServerApp.token` silently ignored — auth returns HTML

**Symptom**: Auth test with known token returns HTML login page (302) instead of JSON:
```
curl -s http://127.0.0.1:8889/api/kernels -H "Authorization: token ..." → HTML
```

**Cause**: `--ServerApp.token` is deprecated in Jupyter Server 2.x. The flag is accepted without error but completely ignored — server generates a random token internally.

**Fix**: Use `--IdentityProvider.token="$MCP_TOKEN"` instead.

**Verification**: `curl -s http://127.0.0.1:8889/api/kernels -H "Authorization: token $(cat ~/SageMaker/mcp-isolated-token)"` → `[]`

---

### 12. Permission prompt when inserting cells

**Symptom**: Claude responds with "I need your permission to write to the notebook file. Could you allow write access?"

**Cause**: `permission_mode = 'acceptEdits'` only auto-approves Claude's built-in file write tools. MCP tool calls (`mcp__jupyter__insert_cell`, etc.) are a separate permission category and still prompt.

**Fix**: Use `permission_mode = 'bypassPermissions'` which disables ALL permission checks including MCP tool calls. Set in `jupyter_server_config.py`:
```python
c.ClaudeExtensionApp.permission_mode = 'bypassPermissions'
```

---

### 13. Chat session still shows ConnectionRefused after MCP server starts

**Symptom**: MCP server is running (`ss -tlnp` shows port 8889) but the Claude chat session still reports ConnectionRefused.

**Cause**: The Claude agent SDK connects to the MCP server at session start and caches the result. An existing session that started before the MCP server was up retains the failed state.

**Fix**: Open a **new chat session** in the JupyterLab plugin (close current chat tab, open a new one). The new session connects fresh.

---

## Working startup command (manual / for restarts)

When the primary server is restarted manually (e.g., after config change), the MCP server must be restarted too:

```bash
# Kill stale process
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
curl -s http://127.0.0.1:8889/mcp/healthz \
  -H "Authorization: token $(cat ~/SageMaker/mcp-isolated-token)"
# → {"status":"healthy",...} = working
```

Then open a **new** chat session in the plugin.

---

## Diagnostic quick-checks

| Check | Command | Expected |
|-------|---------|----------|
| MCP server process | `ps aux \| grep "mcp-isolated-env" \| grep -v grep` | PID line visible |
| Port listening | `ss -tlnp \| grep 8889` | `LISTEN ... 127.0.0.1:8889` |
| Auth working | `curl -s http://127.0.0.1:8889/api/kernels -H "Authorization: token $(cat ~/SageMaker/mcp-isolated-token)"` | `[]` |
| Extension loaded | `curl -s http://127.0.0.1:8889/mcp/healthz -H "Authorization: token $(cat ~/SageMaker/mcp-isolated-token)"` | `{"status":"healthy",...}` |
| Plugin config present | `grep -c jcf ~/.jupyter/jupyter_server_config.py` | `> 0` |
| Permission mode | `grep permission_mode ~/.jupyter/jupyter_server_config.py` | `bypassPermissions` |
| Token file exists | `ls -la ~/SageMaker/mcp-isolated-token` | 600, ec2-user owner |

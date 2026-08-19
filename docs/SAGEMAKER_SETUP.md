# Jupyter Claude Plugin — SageMaker Notebook Setup Guide

> This guide covers installing and configuring the `jupyter-claude-plugin` on an **AWS SageMaker
> notebook instance** (classic or Studio with JupyterLab 4). All steps are performed from the
> JupyterLab terminal inside the instance.
>
> For local dev setup, see [USER_GUIDE.md](USER_GUIDE.md).

## Contents

- [Prerequisites](#prerequisites)
- [Step 1 — Verify the environment](#step-1--verify-the-environment)
- [Step 2 — Install the plugin](#step-2--install-the-plugin)
- [Step 3 — Configure the plugin](#step-3--configure-the-plugin)
- [Step 4 — Restart the Jupyter server](#step-4--restart-the-jupyter-server)
- [Step 5 — Verify the setup](#step-5--verify-the-setup)
- [Step 6 — Make the install persistent](#step-6--make-the-install-persistent)
- [Manual file update (for testing pre-release changes)](#manual-file-update-for-testing-pre-release-changes)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, confirm the following with your AWS administrator:

1. **SageMaker execution role** — the role attached to your notebook instance must have:

   - `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` on the approved
     Claude inference profiles
   - `logs:CreateLogStream` and `logs:PutLogEvents` on `/aws/jupyter-claude/sessions-dev`
   - This is provisioned by the `dev-sagemaker-execution-role` CloudFormation stack in
     `Claude_Bedrock_CLI`. Confirm with your admin that it has been deployed.
2. **JupyterLab 4** — the plugin requires JupyterLab 4. Classic SageMaker notebook instances
   often ship JupyterLab 3. Confirm in a terminal:

   ```bash
   jupyter lab --version
   # Must be 4.x — if not, ask your admin to upgrade the instance or use SageMaker Studio
   ```
3. **Internet access** — the instance needs outbound access to PyPI (`pypi.org`) to install
   the plugin. Bedrock calls go via AWS-internal endpoints and do not require extra egress rules.

---

## Step 1 — Verify the environment

Open a terminal in JupyterLab (**File → New → Terminal**) and run:

```bash
# 1. Confirm JupyterLab version
jupyter lab --version          # must be 4.x

# 2. Confirm Python version
python --version               # 3.10 or higher

# 3. Confirm Bedrock is reachable via the execution role (no profile needed)
aws bedrock list-inference-profiles --region us-east-2 \
  | python -c "import sys,json; [print(p['inferenceProfileId']) for p in json.load(sys.stdin)['inferenceProfileSummaries'] if 'claude' in p['inferenceProfileId']]"
# Expected: us.anthropic.claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5-20251001-v1:0
```

If the Bedrock call fails with `AccessDeniedException`, the execution role is missing
the required policy — contact your admin before proceeding.

---

## Step 2 — Install the plugin

From the JupyterLab terminal:

```bash
pip install --pre jupyter-claude-plugin
```

Verify all three server extensions are registered:

```bash
jupyter server extension list | grep -E "jupyter_claude|jupyter_mcp"
# Expected output (all three must show "enabled"):
#   jupyter_claude          enabled  OK
#   jupyter_mcp_server      enabled  OK
#   jupyter_mcp_tools       enabled  OK  (or jupyter_mcp_server_tools)
```

Verify the frontend extension:

```bash
jupyter labextension list | grep claude
# Expected:
#   @dckartasoft/jupyter-claude v0.1.0-alpha.1 enabled OK
```

---

## Step 3 — Configure the plugin

Create (or edit) `~/.jupyter/jupyter_server_config.py`:

```bash
mkdir -p ~/.jupyter
cat >> ~/.jupyter/jupyter_server_config.py << 'EOF'
c = get_config()  # noqa

# Backend: use AWS Bedrock with IMDS credentials from the execution role
c.ClaudeExtensionApp.backend = "bedrock"
c.ClaudeExtensionApp.aws_region = "us-east-2"          # Bedrock governance region

# DO NOT set aws_profile — leave it empty so credentials come from the execution role
# c.ClaudeExtensionApp.aws_profile = ""  (this is the default; no need to set it)

# Bedrock inference profile IDs
c.ClaudeExtensionApp.default_opus_model   = "us.anthropic.claude-opus-4-7"
c.ClaudeExtensionApp.default_sonnet_model = "us.anthropic.claude-sonnet-4-6"
c.ClaudeExtensionApp.default_haiku_model  = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# Auto-approve cell insertions (recommended for data science workflows)
c.ClaudeExtensionApp.permission_mode = "acceptEdits"

# Per-user CloudWatch session tracking
c.ClaudeExtensionApp.cloudwatch_log_group = "/aws/jupyter-claude/sessions-dev"
c.ClaudeExtensionApp.cloudwatch_region    = "us-east-2"   # region the log group is in
EOF
```

> **Why no `aws_profile`?** Named profiles read from `~/.aws/credentials`, which the SageMaker
> execution role does not populate. Leaving the trait empty tells the plugin to use the standard
> AWS credential chain, which automatically finds the instance metadata (IMDS) credentials
> provided by the execution role.

---

## Step 4 — Restart the Jupyter server

The config file is only read at server startup. You must restart Jupyter for changes to take effect.

### Classic SageMaker notebook instances

```bash
sudo systemctl restart jupyter-server
```

If that command is not found, try:

```bash
sudo initctl restart jupyter-server
# or
sudo service jupyter restart
```

The browser will show **"Server connection lost"**. Wait ~30 seconds, then reload the page.

### SageMaker Studio (JupyterLab app)

From the menu bar: **File → Shut Down**. Then relaunch the JupyterLab space from the
SageMaker Studio control panel.

---

## Step 5 — Verify the setup

After the page reloads:

1. **Look for the Claude icon** in the right sidebar (a small spark/lightning bolt icon).
   Click it to open the chat panel.
2. **Check the connection banner** at the top of the panel — it should read:

   ```
   Connected — bedrock / us.anthropic.claude-sonnet-4-6
   ```
3. **Send a test message** — type `"hello"` and press Enter. You should get a response within
   a few seconds.
4. **Verify CloudWatch logging** — from a terminal with admin AWS credentials (not on the
   SageMaker instance itself), check for the new log stream:

   ```bash
   aws logs describe-log-streams \
     --log-group-name /aws/jupyter-claude/sessions-dev \
     --region us-east-1 \
     --order-by LastEventTime \
     --descending \
     --profile kartasoft-dev \
     --query "logStreams[0]"
   # Expected: a stream named like "your-username/550e8400-..."
   ```

If the panel shows a red error banner instead of "Connected", see [Troubleshooting](#troubleshooting).

---

## Step 6 — Make the install persistent (lifecycle configuration)

SageMaker re-initialises the Jupyter environment on every **Stop → Start** cycle. A lifecycle
configuration script runs automatically before JupyterLab starts, so changes are in place by
the time you open the browser.

> **Important:** Do NOT add `sudo systemctl restart jupyter-server` to a lifecycle script.
> The script already runs before Jupyter starts — a manual service restart breaks
> SageMaker's auth handler and causes login prompts on every page load.

### The script

```bash
#!/bin/bash
set -euo pipefail

# Full paths — lifecycle scripts run as root before conda is activated
CONDA_DIR=/home/ec2-user/anaconda3
PIP="$CONDA_DIR/bin/pip"
PYTHON="$CONDA_DIR/bin/python"
JUPYTER_CONFIG=/home/ec2-user/.jupyter/jupyter_server_config.py

# ── 1. Install / upgrade plugin ───────────────────────────────────────────
echo "[jupyter-claude] Installing plugin..."
$PIP install --quiet --pre jupyter-claude-plugin --root-user-action=ignore --no-deps

# Fix ownership so JupyterLab (running as ec2-user) can serve the static bundle
chown -R ec2-user:ec2-user /home/ec2-user/anaconda3/share/jupyter/labextensions/@dckartasoft/ 2>/dev/null || true

# ── 2. Append Claude config (idempotent — skips if already present) ───────
echo "[jupyter-claude] Configuring plugin..."
if ! grep -q "ClaudeExtensionApp" "$JUPYTER_CONFIG" 2>/dev/null; then
  cat >> "$JUPYTER_CONFIG" << 'PYEOF'

# ── jupyter-claude-plugin ─────────────────────────────────────────────────
c.ClaudeExtensionApp.backend = "bedrock"
c.ClaudeExtensionApp.aws_region = "us-east-2"
c.ClaudeExtensionApp.default_opus_model   = "us.anthropic.claude-opus-4-7"
c.ClaudeExtensionApp.default_sonnet_model = "us.anthropic.claude-sonnet-4-6"
c.ClaudeExtensionApp.default_haiku_model  = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
c.ClaudeExtensionApp.permission_mode      = "acceptEdits"
c.ClaudeExtensionApp.cloudwatch_log_group = "/aws/jupyter-claude/sessions-dev"
c.ClaudeExtensionApp.cloudwatch_region    = "us-east-2"
PYEOF
  echo "[jupyter-claude] Config written."
else
  echo "[jupyter-claude] Config already present, skipping."
fi

# ── 3. Re-enable default file browser ────────────────────────────────────
# jupyter-server-nbmodel (pulled in as a dependency) disables the default
# JupyterLab file browser and replaces it with its own. This restores it so
# notebooks are visible in the left sidebar.
LABCONFIG_DIR=$($PYTHON -c "import jupyter_core.paths as p; print(p.jupyter_config_dir())")/labconfig
mkdir -p "$LABCONFIG_DIR"
cat > "$LABCONFIG_DIR/page_config.json" << 'EOF'
{
  "enabledExtensions": {
    "@jupyterlab/filebrowser-extension:defaultFileBrowser": true
  }
}
EOF
echo "[jupyter-claude] File browser re-enabled."

echo "[jupyter-claude] Setup complete."
```

### Attaching the lifecycle configuration

1. In the AWS console, go to **SageMaker → Notebook → Lifecycle configurations**.
2. Click **Create configuration**, name it `jupyter-claude-plugin-setup`.
3. Select the **Start notebook** tab and paste the script above.
4. Click **Create configuration**.
5. Go to **Notebook instances → your instance → Actions → Stop**.
6. Once stopped: **Actions → Edit → Lifecycle configuration → select `jupyter-claude-plugin-setup` → Update**.
7. **Actions → Start** — the script runs automatically before JupyterLab comes up.
8. Open JupyterLab from the console link once the instance is **InService**.

The file browser and Claude icon will be present from the first page load.

---

## Manual file update (for testing pre-release changes)

If you need to test modified plugin files before a new PyPI release:

### 1. Upload files via JupyterLab

Use the **upload button** (↑ icon) in the JupyterLab file browser to upload `config.py`
and/or `chat_handler.py` into your home directory (`/home/ec2-user/` or `/root/`).

### 2. Copy to the installed location

From the terminal:

```bash
# Find the installed package location
SITE=$(pip show jupyter-claude-plugin | grep Location | awk '{print $2}')
echo "Installing to: $SITE/jupyter_claude/"

# Copy the updated files
cp ~/config.py      $SITE/jupyter_claude/config.py
cp ~/chat_handler.py $SITE/jupyter_claude/chat_handler.py

# Confirm
python -c "from jupyter_claude.config import ClaudeExtensionApp; \
           print('cloudwatch_log_group' in ClaudeExtensionApp.class_traits())"
# → True
```

### 3. Restart the Jupyter server

```bash
sudo systemctl restart jupyter-server
```

Reload the browser page after ~30 seconds.

> **Note:** Manually copied files are overwritten by the next `pip install --upgrade`.
> This workflow is for testing only — raise a PR to get changes into a proper release.

---

## Troubleshooting

### The Claude icon does not appear in the sidebar

```bash
# 1. Confirm extension is enabled
jupyter labextension list | grep claude
# Must show: @dckartasoft/jupyter-claude  enabled OK

# 2. Check for page_config.json disabling it
cat "$(python -c 'import sys; print(sys.prefix)')/etc/jupyter/labconfig/page_config.json"
# dckartasoft-jupyter-claude must NOT appear in disabledExtensions or lockedExtensions
# If it does: echo '{"disabledExtensions":{},"lockedExtensions":{}}' > <that path>
# Then restart the Jupyter server
```

### "Connected" banner never appears / red error

```bash
# Check the server log
sudo journalctl -u jupyter-server -n 50 --no-pager
# or
tail -100 /var/log/jupyter.log 2>/dev/null || journalctl -u jupyter-server -n 100
```

Common causes on SageMaker:

| Symptom in log                                 | Cause                                               | Fix                                                                           |
| ---------------------------------------------- | --------------------------------------------------- | ----------------------------------------------------------------------------- |
| `AccessDeniedException: bedrock:InvokeModel` | Execution role missing Bedrock policy               | Ask admin to attach the policy                                                |
| `Could not connect to MCP server`            | `jupyter_mcp_server` not installed or not running | Re-run`pip install --pre jupyter-claude-plugin` and restart                 |
| `NoCredentialError`                          | `aws_profile` set to a value that doesn't exist   | Remove`aws_profile` from config — leave it empty                           |
| `EndpointResolutionError`                    | Wrong`aws_region`                                 | Confirm Bedrock is enabled in that region; us-east-2 is the governance region |

### CloudWatch logs not appearing

```bash
# Check the execution role has the logging policy attached
aws iam list-attached-role-policies \
  --role-name <your-execution-role-name> \
  --query "AttachedPolicies[?contains(PolicyName,'JupyterClaude')]"
```

If no policy appears, the `dev-sagemaker-execution-role` CloudFormation stack has not been
deployed, or the instance is using a different execution role. Contact your AWS admin.

### Plugin installs but `jupyter server extension list` shows "not enabled"

```bash
jupyter server extension enable jupyter_claude --sys-prefix
sudo systemctl restart jupyter-server
```

### `pip install` fails with network error

The instance may be in a VPC without internet access. Options:

- Use a VPC endpoint for PyPI (or a private mirror like CodeArtifact)
- Ask your admin to allow outbound HTTPS to `pypi.org` from the instance's security group
- As a workaround, upload the wheel directly (see [Manual file update](#manual-file-update-for-testing-pre-release-changes))

---

## Related docs

- [USER_GUIDE.md](USER_GUIDE.md) — general install and usage guide (local dev)
- [STATUS.md](STATUS.md) — current release state, config surface, uncommitted changes
- `Claude_Bedrock_CLI/Docs/SAGEMAKER-JUPYTER-INTEGRATION.md` — CloudFormation templates and
  Sceptre configs required by this setup (admin/infrastructure reference)

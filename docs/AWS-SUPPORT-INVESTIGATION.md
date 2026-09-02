# AWS Support — Technical Investigation Brief
## `jupyter-server-nbmodel` Incompatibility on SageMaker Classic Notebook Instances

**Account:** 201155390384  
**Region:** us-east-2  
**Instance:** `dev-al2023-dcdevmlps-v0-notebook` (JupyterLab 4.6.3, Amazon Linux 2023)  
**Date prepared:** 2026-08-25  

---

## The Core Issue

Installing `jupyter-mcp-server>=1.0` on a SageMaker classic notebook instance renders notebooks
unusable. Every notebook open produces a persistent spinner and repeated "Session expired" dialogs.

**Root cause:** `jupyter-mcp-server>=1.0` depends on `jupyter-collaboration`, which installs
`@datalayer/jupyter-server-nbmodel` (v0.2.8) — a JupyterLab frontend extension that implements
Y-Doc (CRDT collaborative editing). On every notebook document open, this extension issues
session-management requests to the server. SageMaker's authentication reverse proxy rejects these
with:

```json
{"reason": "unknown_session", "sessionId": ""}
```

This is a protocol mismatch between Datalayer's real-time collaboration model and SageMaker's
session model. It is not a configuration error — no amount of server or client configuration
resolves it.

---

## What Was Tried (Chronological)

### 1. Disable the Python server extension
```bash
jupyter server extension disable jupyter_server_nbmodel --sys-prefix
```
**Outcome:** Disables the Python side only. The frontend labextension bundle is still served by
JupyterLab and continues to intercept notebook opens. No improvement.

### 2. Disable via `page_config.json` — wrong extension name
```json
{ "disabledExtensions": { "@jupyter/collaboration-extension": true } }
```
**Outcome:** Catastrophic. `@jupyter/collaboration-extension` is the notebook document model
provider in JupyterLab 4.6.x — disabling it broke notebook opens entirely. Additionally,
a user-level `page_config.json` **replaces** the system-level defaults rather than merging,
wiping SageMaker's own UI configuration in the process.

### 3. Disable via `page_config.json` — correct extension name
```json
{ "disabledExtensions": { "@datalayer/jupyter-server-nbmodel": true } }
```
**Outcome:** Suppressed the frontend in that session. Fragile — any pip reinstall or upgrade
re-enables it. Does not prevent server-side session requests that have already been queued.
Not a reliable fix.

### 4. Clear Y-Doc file ID databases
```bash
rm ~/.jupyter_ystore.db ~/.local/share/jupyter/file_id_manager.db
```
**Outcome:** Cleared a secondary symptom (stale file ID mismatch causing extra "session expired"
dialogs). Did not fix the underlying `unknown_session` rejection from the SageMaker proxy.

### 5. Physical removal of the labextension bundle
```bash
rm -rf $JUPYTER_ENV/share/jupyter/labextensions/@datalayer/jupyter-server-nbmodel
```
**Outcome:** Works when run before JupyterLab starts. Removes the frontend without disturbing
the Python MCP endpoint. However, SageMaker's lifecycle scripts run in a backgrounded subshell
(required to avoid the 5-minute lifecycle timeout), and JupyterLab frequently loads the extension
before the `rm -rf` completes — a race condition that cannot be reliably eliminated.

---

## Current Workaround

A second, isolated Jupyter server process runs on port `8889` (separate from SageMaker's main
server on `:8443`). This secondary server explicitly excludes `jupyter_server_nbmodel` from its
extension map at startup — no race condition, no scrub required. A developer connects to it from
their local machine via an SSM port-forward tunnel.

This workaround avoids the conflict entirely but adds operational overhead (SSM tunnel management,
separate token distribution via SSM Parameter Store) and is not a long-term solution. The goal
remains a supported, direct installation of `jupyter-mcp-server` on the SageMaker instance.

---

## Question for AWS Support

**Is the `{"reason": "unknown_session"}` response from SageMaker's authentication proxy when
`@datalayer/jupyter-server-nbmodel` issues Y-Doc session-management requests a known
incompatibility?**

Specifically:
- Is there a supported way to install `jupyter-mcp-server>=1.0` on a SageMaker classic notebook
  instance without triggering this conflict?
- Is a fix planned for the SageMaker proxy to handle these Y-Doc session requests gracefully?
- If classic notebook instances are not supported for this use case, is SageMaker Studio
  (JupyterLab 4, customer VPC-native) the recommended migration path?

---

## Dependency Chain (for reference)

```
jupyter-claude-plugin (this project)
  └── jupyter-mcp-server>=1.0
        └── jupyter-collaboration>=2.0
              └── jupyter-server-nbmodel
                    └── @datalayer/jupyter-server-nbmodel  ← the problematic frontend extension
```

The conflict is in the transitive dependency — `jupyter-mcp-server` itself is a lightweight
Python server extension. The issue is introduced two levels deep by `jupyter-collaboration`.

---

*Investigation conducted 2026-08-19 to 2026-08-20. Brief prepared 2026-08-25.*  
*Plugin repo: `~/Dev/Jupyter-Claude_Plugin`. Federated workaround repo: `~/Dev/Jupyter-Claude-Federated`.*

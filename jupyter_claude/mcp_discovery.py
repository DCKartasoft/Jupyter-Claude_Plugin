"""Enumerate MCP servers registered in the user's Claude Code config."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _claude_config_path() -> Path:
    return Path(os.path.expanduser("~/.claude.json"))


def list_user_mcp_servers() -> dict[str, dict]:
    """Return {name: config} for MCP servers in ~/.claude.json (user scope).

    Returns an empty dict if the file is missing, unreadable, or lacks the
    `mcpServers` key. Never raises.
    """
    path = _claude_config_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        return {}
    return {name: cfg for name, cfg in servers.items() if isinstance(cfg, dict)}


def describe_server(cfg: dict) -> str:
    """Return a short human-readable description of an MCP server config."""
    if cfg.get("type") == "http":
        return f"http {cfg.get('url', '')}"
    cmd = cfg.get("command")
    if cmd:
        args = cfg.get("args", [])
        return f"stdio {cmd} {' '.join(str(a) for a in args)}".strip()
    return "unknown"

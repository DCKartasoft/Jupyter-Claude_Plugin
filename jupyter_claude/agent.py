import os

from claude_agent_sdk import ClaudeAgentOptions

from .mcp_discovery import list_user_mcp_servers


def _build_mcp_servers(cfg, jupyter_mcp_url: str, jupyter_token: str) -> dict:
    """Build the mcp_servers dict, honoring enabled_mcp_servers filter.

    `jupyter` is always included (it's how Claude reads/writes cells). Everything
    else is looked up from ~/.claude.json and included only if in
    cfg.enabled_mcp_servers.
    """
    servers: dict = {
        "jupyter": {
            "type": "http",
            "url": jupyter_mcp_url,
            "headers": {"Authorization": f"token {jupyter_token}"},
        }
    }
    user_servers = list_user_mcp_servers()
    enabled = set(cfg.enabled_mcp_servers or [])
    for name, sconf in user_servers.items():
        if name == "jupyter":
            continue
        if name not in enabled:
            continue
        servers[name] = sconf
    return servers


def _allowed_tools_for(servers: dict) -> list[str]:
    return [f"mcp__{name}__*" for name in servers]


def build_options(
    cfg,
    jupyter_mcp_url: str,
    jupyter_token: str,
    *,
    tier_override: str | None = None,
) -> ClaudeAgentOptions:
    env: dict[str, str] = {}

    if cfg.backend == "bedrock":
        env["CLAUDE_CODE_USE_BEDROCK"] = "1"
        env["AWS_REGION"] = cfg.aws_region
        env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = cfg.default_opus_model
        env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = cfg.default_sonnet_model
        env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = cfg.default_haiku_model

        tier_map = {
            "opus": cfg.default_opus_model,
            "sonnet": cfg.default_sonnet_model,
            "haiku": cfg.default_haiku_model,
        }
        selected_tier = tier_override or cfg.main_model_tier
        env["ANTHROPIC_MODEL"] = tier_map[selected_tier]

        if cfg.aws_profile:
            env["AWS_PROFILE"] = cfg.aws_profile

        for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
                    "AWS_PROFILE", "AWS_BEARER_TOKEN_BEDROCK", "AWS_CONFIG_FILE",
                    "AWS_SHARED_CREDENTIALS_FILE"):
            if var in os.environ and var not in env:
                env[var] = os.environ[var]
    else:
        if "ANTHROPIC_API_KEY" in os.environ:
            env["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
        env["ANTHROPIC_MODEL"] = cfg.model

    mcp_servers = _build_mcp_servers(cfg, jupyter_mcp_url, jupyter_token)
    allowed_tools = _allowed_tools_for(mcp_servers)

    return ClaudeAgentOptions(
        env=env,
        system_prompt=cfg.system_prompt,
        mcp_servers=mcp_servers,
        allowed_tools=allowed_tools,
        permission_mode=cfg.permission_mode,
    )

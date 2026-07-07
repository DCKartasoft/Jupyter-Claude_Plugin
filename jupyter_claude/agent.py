import os

from claude_agent_sdk import ClaudeAgentOptions


def build_options(cfg, jupyter_mcp_url: str, jupyter_token: str) -> ClaudeAgentOptions:
    env: dict[str, str] = {}

    if cfg.backend == "bedrock":
        env["CLAUDE_CODE_USE_BEDROCK"] = "1"
        env["AWS_REGION"] = cfg.aws_region
        env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = cfg.default_opus_model
        env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = cfg.default_sonnet_model
        env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = cfg.default_haiku_model

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

    mcp_servers = {
        "jupyter": {
            "type": "http",
            "url": jupyter_mcp_url,
            "headers": {"Authorization": f"token {jupyter_token}"},
        }
    }

    return ClaudeAgentOptions(
        env=env,
        system_prompt=cfg.system_prompt,
        mcp_servers=mcp_servers,
        allowed_tools=["mcp__jupyter__*"],
        permission_mode=cfg.permission_mode,
    )

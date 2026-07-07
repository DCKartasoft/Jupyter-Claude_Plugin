from jupyter_server.extension.application import ExtensionApp
from traitlets import Bool, Enum, Unicode


class ClaudeExtensionApp(ExtensionApp):
    name = "jupyter_claude"

    backend = Enum(
        ["anthropic", "bedrock"],
        default_value="anthropic",
        config=True,
        help="Which Claude backend to use. `anthropic` calls the Anthropic API "
        "directly and requires ANTHROPIC_API_KEY in the environment. `bedrock` "
        "routes through AWS Bedrock using the standard AWS credential chain.",
    )

    model = Unicode(
        "claude-opus-4-8",
        config=True,
        help="Model identifier. For `anthropic` backend, use a plain model name "
        "(e.g. `claude-opus-4-8`). For `bedrock`, use a cross-region inference "
        "profile ID (e.g. `us.anthropic.claude-opus-4-8`).",
    )

    aws_region = Unicode(
        "us-east-1",
        config=True,
        help="AWS region for the Bedrock backend. Ignored when backend is `anthropic`.",
    )

    aws_profile = Unicode(
        "",
        config=True,
        help="AWS named profile for the Bedrock backend. When non-empty, "
        "`AWS_PROFILE` is set in the SDK subprocess env so it picks up shared "
        "SSO credentials from `~/.aws/config`. Empty means fall back to whatever "
        "credentials the Jupyter process already has. Ignored when backend is "
        "`anthropic`.",
    )

    default_opus_model = Unicode(
        "us.anthropic.claude-opus-4-7",
        config=True,
        help="Bedrock inference-profile ID for the Opus tier. Used only when "
        "backend is `bedrock`.",
    )

    default_sonnet_model = Unicode(
        "us.anthropic.claude-sonnet-4-6",
        config=True,
        help="Bedrock inference-profile ID for the Sonnet tier. Used only when "
        "backend is `bedrock`.",
    )

    default_haiku_model = Unicode(
        "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        config=True,
        help="Bedrock inference-profile ID for the Haiku tier. Used only when "
        "backend is `bedrock`.",
    )

    system_prompt = Unicode(
        "You are a helpful assistant collaborating with a data scientist inside "
        "a JupyterLab notebook. You can read, write, and execute notebook cells "
        "through the Jupyter MCP tools available to you. Prefer small, "
        "reversible steps. When generating code, explain the plan briefly first, "
        "then produce a single fenced code block the user can drop into a cell.",
        config=True,
        help="System prompt sent to Claude on every conversation.",
    )

    jupyter_mcp_url = Unicode(
        "",
        config=True,
        help="URL of the Jupyter MCP server. Empty string means auto-detect from "
        "the running Jupyter server's port and token.",
    )

    permission_mode = Enum(
        ["default", "acceptEdits", "plan", "bypassPermissions"],
        default_value="default",
        config=True,
        help="Claude Agent SDK permission mode. `default` prompts on tool use; "
        "`acceptEdits` auto-approves edits; `bypassPermissions` disables all "
        "permission checks (unsafe).",
    )

    verbose = Bool(
        False,
        config=True,
        help="Log every message the SDK produces at INFO level.",
    )

    def initialize_settings(self):
        self.settings["jclaude_config"] = self
        if self.backend == "bedrock":
            self.log.info(
                "jupyter_claude configured: backend=bedrock region=%s profile=%s "
                "opus=%s sonnet=%s haiku=%s",
                self.aws_region,
                self.aws_profile or "<from process env>",
                self.default_opus_model,
                self.default_sonnet_model,
                self.default_haiku_model,
            )
        else:
            self.log.info(
                "jupyter_claude configured: backend=anthropic model=%s",
                self.model,
            )

    def initialize_handlers(self):
        from .chat_handler import ChatWebSocketHandler
        from .routes import HelloRouteHandler

        self.handlers.extend([
            (r"/jupyter-claude/hello", HelloRouteHandler),
            (r"/jupyter-claude/chat", ChatWebSocketHandler),
        ])

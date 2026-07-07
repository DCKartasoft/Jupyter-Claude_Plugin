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
        self.log.info(
            "jupyter_claude configured: backend=%s model=%s region=%s",
            self.backend,
            self.model,
            self.aws_region if self.backend == "bedrock" else "n/a",
        )

    def initialize_handlers(self):
        from .chat_handler import ChatWebSocketHandler
        from .routes import HelloRouteHandler

        self.handlers.extend([
            (r"/jupyter-claude/hello", HelloRouteHandler),
            (r"/jupyter-claude/chat", ChatWebSocketHandler),
        ])

import json
from pathlib import Path

from jupyter_server.extension.application import ExtensionApp
from traitlets import Bool, Enum, Int, List, Unicode, default


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
        config=True,
        help="Model identifier. For `anthropic` backend, use a plain model name "
        "(e.g. `claude-opus-latest`). For `bedrock`, use a cross-region inference "
        "profile ID (e.g. `us.anthropic.claude-opus-5-5`).",
    )

    @default("model")
    def _default_model(self):
        return self._models_json().get("direct", "claude-opus-latest")

    aws_region = Unicode(
        config=True,
        help="AWS region for the Bedrock backend. Ignored when backend is `anthropic`. "
        "Defaults to `aws_region` in jupyter_claude_models.json, else `us-east-1`. "
        "Must match the inference-profile prefix of the model IDs (e.g. `eu-` "
        "profiles for EU regions) to keep inference within the intended geography.",
    )

    @default("aws_region")
    def _default_aws_region(self):
        return self._models_json().get("aws_region", "us-east-1")

    aws_profile = Unicode(
        "",
        config=True,
        help="AWS named profile for the Bedrock backend. When non-empty, "
        "`AWS_PROFILE` is set in the SDK subprocess env so it picks up shared "
        "SSO credentials from `~/.aws/config`. Empty means fall back to whatever "
        "credentials the Jupyter process already has. Ignored when backend is "
        "`anthropic`.",
    )

    default_fable_model = Unicode(
        config=True,
        help="Bedrock inference-profile ID for the Fable tier. Used only when "
        "backend is `bedrock`.",
    )

    @default("default_fable_model")
    def _default_fable_model(self):
        return self._models_json().get("fable", "us.anthropic.claude-fable-5-1")

    default_opus_model = Unicode(
        config=True,
        help="Bedrock inference-profile ID for the Opus tier. Used only when "
        "backend is `bedrock`.",
    )

    @default("default_opus_model")
    def _default_opus_model(self):
        return self._models_json().get("opus", "us.anthropic.claude-opus-5-5")

    default_sonnet_model = Unicode(
        config=True,
        help="Bedrock inference-profile ID for the Sonnet tier. Used only when "
        "backend is `bedrock`.",
    )

    @default("default_sonnet_model")
    def _default_sonnet_model(self):
        return self._models_json().get("sonnet", "us.anthropic.claude-sonnet-5-5")

    default_haiku_model = Unicode(
        config=True,
        help="Bedrock inference-profile ID for the Haiku tier. Used only when "
        "backend is `bedrock`.",
    )

    @default("default_haiku_model")
    def _default_haiku_model(self):
        return self._models_json().get("haiku", "us.anthropic.claude-haiku-5-5")

    main_model_tier = Enum(
        ["fable", "opus", "sonnet", "haiku"],
        default_value="sonnet",
        config=True,
        help="Which tier the main conversation model runs on. `opus` is "
        "highest quality but slowest; `sonnet` (default) is a good balance; "
        "`haiku` is fastest. On Bedrock this sets ANTHROPIC_MODEL to the "
        "corresponding default_{tier}_model. On Anthropic direct this is "
        "ignored — use the `model` trait instead.",
    )

    system_prompt = Unicode(
        "You are a helpful assistant collaborating with a data scientist inside "
        "a JupyterLab notebook.\n\n"
        "You may have access to Jupyter MCP tools (`mcp__jupyter__*`) that can "
        "read, write, and execute notebook cells. Use them ONLY when the user's "
        "message clearly requires notebook access — e.g. they ask you to "
        "insert / modify / execute a cell, or their question genuinely depends "
        "on notebook state not already provided in the message.\n\n"
        "IMPORTANT: user messages often include a `<notebook_snapshot>` block "
        "with the current cell contents. When present, use it as your source "
        "of truth for the notebook state and DO NOT call `read_notebook` or "
        "`read_cell` — that snapshot already has what you need. Only call the "
        "Jupyter tools when you need to *write* (insert / overwrite / execute) "
        "a cell, or when the snapshot was explicitly marked truncated and you "
        "need a specific cell that's missing.\n\n"
        "For general questions, code snippets, explanations, or conversation, "
        "respond directly with NO tool calls. Prefer small reversible steps. "
        "When generating code, briefly explain the plan first, then either "
        "produce a fenced code block or insert the cell directly via the "
        "appropriate `mcp__jupyter__` tool if the user asked for insertion.",
        config=True,
        help="System prompt sent to Claude on every conversation. The default "
        "steers Claude toward using the `<notebook_snapshot>` shipped in each "
        "user message and away from redundant `read_notebook`/`read_cell` MCP "
        "calls, which noticeably improves chat latency.",
    )

    notebook_snapshot_max_cells = Int(
        50,
        config=True,
        help="How many cells to include in the `<notebook_snapshot>` prefixed "
        "to each user message. 0 disables snapshots entirely (Claude falls "
        "back to read_notebook — slower). 50 (default) covers most notebooks. "
        "Larger notebooks are truncated with a marker; Claude will call "
        "`read_cell` for omitted cells only if the request needs them.",
    )

    notebook_snapshot_max_source_chars = Int(
        2000,
        config=True,
        help="Per-cell character cap for source code in the notebook snapshot. "
        "Cells longer than this are truncated with `…(N more chars)`. 0 "
        "disables truncation.",
    )

    jupyter_mcp_url = Unicode(
        "",
        config=True,
        help="URL of the Jupyter MCP server. Empty string means auto-detect from "
        "the running Jupyter server's port and token.",
    )

    jupyter_mcp_token = Unicode(
        "",
        config=True,
        help="Auth token for the Jupyter MCP server. Empty string (default) uses "
        "the running Jupyter server's own token — correct when the MCP server is "
        "the same process. Set this when the MCP server runs in a separate isolated "
        "environment (e.g. on SageMaker, where the MCP server is on port 8889 and "
        "has its own token distinct from the primary server on 8443).",
    )

    enabled_mcp_servers = List(
        trait=Unicode(),
        default_value=["jupyter"],
        config=True,
        help="Names of MCP servers Claude may connect to. Servers are "
        "discovered from ~/.claude.json (user-scope Claude Code config) plus "
        "the built-in `jupyter` server. Fewer servers = faster startup. "
        "`jupyter` is always included even if omitted here.",
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

    cloudwatch_log_group = Unicode(
        "",
        config=True,
        help="CloudWatch Logs log group name for per-user session tracking. "
        "Empty (default) disables CloudWatch emission. "
        "Example: `/aws/jupyter-claude/sessions`. "
        "The process credentials (SageMaker execution role or ambient AWS profile) "
        "must have logs:CreateLogStream and logs:PutLogEvents on this log group.",
    )

    cloudwatch_region = Unicode(
        "",
        config=True,
        help="AWS region for the CloudWatch Logs client. Empty (default) inherits "
        "from `aws_region`. Override only when the log group is in a different "
        "region than Bedrock (e.g. SageMaker in us-east-1, Bedrock governance "
        "stacks in us-east-2).",
    )

    def _models_json(self):
        try:
            from jupyter_core.paths import jupyter_config_dir
            path = Path(jupyter_config_dir()) / "jupyter_claude_models.json"
        except Exception:
            path = Path.home() / ".jupyter" / "jupyter_claude_models.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                self.log.warning("jupyter_claude: failed to parse %s", path)
        return {}

    # jupyter_claude_models.json key -> trait it overrides.
    _MODELS_JSON_TRAITS = {
        "direct": "model",
        "aws_region": "aws_region",
        "fable": "default_fable_model",
        "opus": "default_opus_model",
        "sonnet": "default_sonnet_model",
        "haiku": "default_haiku_model",
    }

    def initialize_settings(self):
        # The models JSON wins over traits set in jupyter_server_config.py, so a
        # stale config file cannot silently override the per-machine region/models.
        for key, value in self._models_json().items():
            trait = self._MODELS_JSON_TRAITS.get(key)
            if trait and isinstance(value, str) and value:
                setattr(self, trait, value)
        self.settings["jclaude_config"] = self
        if self.backend == "bedrock":
            self.log.info(
                "jupyter_claude configured: backend=bedrock region=%s profile=%s "
                "fable=%s opus=%s sonnet=%s haiku=%s",
                self.aws_region,
                self.aws_profile or "<from process env>",
                self.default_fable_model,
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
        from .routes import HelloRouteHandler, McpServersHandler

        self.handlers.extend([
            (r"/jupyter-claude/hello", HelloRouteHandler),
            (r"/jupyter-claude/chat", ChatWebSocketHandler),
            (r"/jupyter-claude/mcp-servers", McpServersHandler),
        ])

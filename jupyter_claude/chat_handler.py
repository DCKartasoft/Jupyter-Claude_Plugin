import asyncio
import json
import traceback
import uuid
from datetime import datetime, timezone

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = Exception  # type: ignore[assignment,misc]

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    UserMessage,
)
from jupyter_server.base.handlers import JupyterHandler
from tornado import web
from tornado.websocket import WebSocketHandler

from .agent import build_options


class ChatWebSocketHandler(JupyterHandler, WebSocketHandler):
    """One WebSocket = one Claude SDK session. Closed on disconnect."""

    _client: ClaudeSDKClient | None = None
    _tier: str = "sonnet"
    _mcp_url: str = ""
    _token: str = ""
    _session_id: str = ""
    _jupyter_user: str = "unknown"
    _cw_client = None
    _cw_log_group: str = ""
    _cw_log_stream: str = ""

    def check_origin(self, origin: str) -> bool:
        return True

    @web.authenticated
    async def get(self, *args, **kwargs):
        return await super().get(*args, **kwargs)

    async def open(self):
        cfg = self.settings["jclaude_config"]
        self._tier = cfg.main_model_tier
        self._session_id = str(uuid.uuid4())
        self._jupyter_user = self._resolve_user()

        self._mcp_url = cfg.jupyter_mcp_url or self._resolve_mcp_url()
        self._token = self._resolve_token()

        if cfg.cloudwatch_log_group and boto3 is not None:
            region = cfg.cloudwatch_region or cfg.aws_region
            self._cw_client = boto3.client("logs", region_name=region)
            self._cw_log_group = cfg.cloudwatch_log_group
            self._cw_log_stream = f"{self._jupyter_user}/{self._session_id}"
            asyncio.ensure_future(self._init_cw_stream())

        try:
            await self._start_client(cfg)
        except Exception as exc:
            self.log.exception("Failed to start Claude SDK client")
            await self._send({"type": "error", "message": str(exc), "traceback": traceback.format_exc()})
            self.close()

    async def _init_cw_stream(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._create_log_stream)

    def _create_log_stream(self):
        try:
            self._cw_client.create_log_stream(
                logGroupName=self._cw_log_group,
                logStreamName=self._cw_log_stream,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceAlreadyExistsException":
                self.log.warning("CloudWatch log stream creation failed: %s", e)

    def _resolve_mcp_url(self) -> str:
        """Derive MCP URL from the running server's actual port and scheme.

        SageMaker runs Jupyter on HTTPS/8443, not HTTP/8888. Reading the
        serverapp attributes is more reliable than parsing the request host.
        """
        try:
            app = self.serverapp
            port = getattr(app, "port", None) or 8888
            certfile = getattr(app, "certfile", None)
            scheme = "https" if certfile else "http"
            return f"{scheme}://localhost:{port}/mcp"
        except Exception:
            return "http://localhost:8888/mcp"

    def _resolve_user(self) -> str:
        try:
            user = self.current_user
            if user is None:
                return "anonymous"
            if hasattr(user, "username"):
                return user.username
            if hasattr(user, "name"):
                return user.name
            return str(user) or "anonymous"
        except Exception:
            return "unknown"

    async def _start_client(self, cfg):
        options = build_options(cfg, self._mcp_url, self._token, tier_override=self._tier)
        self._client = ClaudeSDKClient(options=options)
        await self._client.__aenter__()
        model_id = self._resolve_model_id(cfg)
        await self._send({
            "type": "ready",
            "backend": cfg.backend,
            "model": model_id,
            "tier": self._tier,
        })

    def _resolve_model_id(self, cfg) -> str:
        if cfg.backend != "bedrock":
            return cfg.model
        tier_map = {
            "opus": cfg.default_opus_model,
            "sonnet": cfg.default_sonnet_model,
            "haiku": cfg.default_haiku_model,
        }
        return tier_map[self._tier]

    async def _stop_client(self):
        if self._client is None:
            return
        client, self._client = self._client, None
        try:
            await client.__aexit__(None, None, None)
        except Exception:
            self.log.exception("Error closing Claude SDK client")

    async def on_message(self, raw: str):
        cfg = self.settings["jclaude_config"]

        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as exc:
            await self._send({"type": "error", "message": f"invalid JSON: {exc}"})
            return

        mtype = msg.get("type")

        if mtype == "mcp_reload":
            await self._stop_client()
            try:
                await self._start_client(cfg)
            except Exception as exc:
                self.log.exception("Failed to restart SDK client on MCP reload")
                await self._send({
                    "type": "error",
                    "message": str(exc),
                    "traceback": traceback.format_exc()
                })
            return

        if mtype == "set_tier":
            new_tier = msg.get("tier")
            if new_tier not in ("opus", "sonnet", "haiku"):
                await self._send({"type": "error", "message": f"unknown tier: {new_tier!r}"})
                return
            if cfg.backend != "bedrock":
                await self._send({
                    "type": "error",
                    "message": "tier switching is only supported on the Bedrock backend"
                })
                return
            self._tier = new_tier
            await self._stop_client()
            try:
                await self._start_client(cfg)
            except Exception as exc:
                self.log.exception("Failed to restart SDK client on tier switch")
                await self._send({
                    "type": "error",
                    "message": str(exc),
                    "traceback": traceback.format_exc()
                })
            return

        if mtype != "user_message":
            await self._send({"type": "error", "message": f"unknown message type: {mtype!r}"})
            return

        if self._client is None:
            await self._send({"type": "error", "message": "SDK client not initialized"})
            return

        try:
            await self._client.query(msg["text"])
            async for m in self._client.receive_response():
                await self._forward(m)
        except Exception as exc:
            self.log.exception("Error while querying Claude")
            await self._send({"type": "error", "message": str(exc), "traceback": traceback.format_exc()})

    async def _forward(self, m):
        if isinstance(m, SystemMessage):
            await self._send({"type": "system", "subtype": m.subtype, "data": m.data})
        elif isinstance(m, AssistantMessage):
            for block in m.content:
                if isinstance(block, TextBlock):
                    await self._send({"type": "assistant_text", "text": block.text})
                elif isinstance(block, ToolUseBlock):
                    await self._send({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
        elif isinstance(m, UserMessage):
            await self._send({"type": "user_echo", "content": [
                {"type": getattr(b, "type", "unknown"), "text": getattr(b, "text", None)}
                for b in m.content
            ]})
        elif isinstance(m, ResultMessage):
            await self._send({
                "type": "result",
                "duration_ms": m.duration_ms,
                "num_turns": m.num_turns,
                "total_cost_usd": m.total_cost_usd,
                "usage": m.usage,
            })
            if self._cw_client:
                asyncio.ensure_future(self._emit_usage(m))

    async def _emit_usage(self, m: ResultMessage):
        cfg = self.settings["jclaude_config"]
        usage = m.usage
        if hasattr(usage, "__dict__"):
            usage_dict = {k: v for k, v in vars(usage).items() if not k.startswith("_")}
        elif isinstance(usage, dict):
            usage_dict = usage
        else:
            usage_dict = {}

        record = {
            "user": self._jupyter_user,
            "session_id": self._session_id,
            "tier": self._tier,
            "model": self._resolve_model_id(cfg),
            "backend": cfg.backend,
            "num_turns": m.num_turns,
            "duration_ms": m.duration_ms,
            "total_cost_usd": m.total_cost_usd,
            **usage_dict,
        }
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._put_log_event, record)

    def _put_log_event(self, record: dict):
        try:
            ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            self._cw_client.put_log_events(
                logGroupName=self._cw_log_group,
                logStreamName=self._cw_log_stream,
                logEvents=[{"timestamp": ts_ms, "message": json.dumps(record)}],
            )
        except Exception:
            self.log.warning("CloudWatch usage emit failed", exc_info=True)

    async def _send(self, payload: dict):
        try:
            self.write_message(json.dumps(payload))
        except Exception:
            self.log.exception("Failed to write to WebSocket")

    def _resolve_token(self) -> str:
        identity = getattr(self.serverapp, "identity_provider", None)
        if identity is not None and hasattr(identity, "token"):
            return identity.token or ""
        return getattr(self.serverapp, "token", "") or ""

    def on_close(self):
        if self._client is not None:
            client, self._client = self._client, None

            async def _cleanup():
                try:
                    await client.__aexit__(None, None, None)
                except Exception:
                    self.log.exception("Error closing Claude SDK client")

            asyncio.ensure_future(_cleanup())

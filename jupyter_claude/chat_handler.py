import json
import traceback

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

    def check_origin(self, origin: str) -> bool:
        return True

    @web.authenticated
    async def get(self, *args, **kwargs):
        return await super().get(*args, **kwargs)

    async def open(self):
        cfg = self.settings["jclaude_config"]
        self._tier = cfg.main_model_tier

        jupyter_port = self.request.host.split(":")[-1] if ":" in self.request.host else "8888"
        self._mcp_url = cfg.jupyter_mcp_url or f"http://localhost:{jupyter_port}/mcp"
        self._token = self._resolve_token()

        try:
            await self._start_client(cfg)
        except Exception as exc:
            self.log.exception("Failed to start Claude SDK client")
            await self._send({"type": "error", "message": str(exc), "traceback": traceback.format_exc()})
            self.close()

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

            import asyncio
            asyncio.ensure_future(_cleanup())

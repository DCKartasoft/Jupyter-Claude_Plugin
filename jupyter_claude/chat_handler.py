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

    def check_origin(self, origin: str) -> bool:
        return True

    @web.authenticated
    async def get(self, *args, **kwargs):
        return await super().get(*args, **kwargs)

    async def open(self):
        cfg = self.settings["jclaude_config"]

        jupyter_port = self.request.host.split(":")[-1] if ":" in self.request.host else "8888"
        mcp_url = cfg.jupyter_mcp_url or f"http://localhost:{jupyter_port}/mcp"

        token = self._resolve_token()

        try:
            options = build_options(cfg, mcp_url, token)
            self._client = ClaudeSDKClient(options=options)
            await self._client.__aenter__()
            await self._send({"type": "ready", "backend": cfg.backend, "model": cfg.model})
        except Exception as exc:
            self.log.exception("Failed to start Claude SDK client")
            await self._send({"type": "error", "message": str(exc), "traceback": traceback.format_exc()})
            self.close()

    async def on_message(self, raw: str):
        if self._client is None:
            await self._send({"type": "error", "message": "SDK client not initialized"})
            return

        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as exc:
            await self._send({"type": "error", "message": f"invalid JSON: {exc}"})
            return

        if msg.get("type") != "user_message":
            await self._send({"type": "error", "message": f"unknown message type: {msg.get('type')!r}"})
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

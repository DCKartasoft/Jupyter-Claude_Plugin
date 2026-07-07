import json

import tornado
from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join

from .chat_handler import ChatWebSocketHandler
from .mcp_discovery import describe_server, list_user_mcp_servers


class HelloRouteHandler(APIHandler):
    @tornado.web.authenticated
    def get(self):
        self.finish(json.dumps({
            "data": (
                "Hello, world!"
                " This is the '/jupyter-claude/hello' endpoint."
                " Try visiting me in your browser!"
            ),
        }))


class McpServersHandler(APIHandler):
    """List MCP servers available to Claude, marking which are enabled."""

    @tornado.web.authenticated
    def get(self):
        cfg = self.settings["jclaude_config"]
        enabled = set(cfg.enabled_mcp_servers or [])

        servers = [{
            "name": "jupyter",
            "description": "Jupyter MCP (built-in, cell R/W/execute)",
            "enabled": True,
            "required": True,
        }]
        for name, sconf in sorted(list_user_mcp_servers().items()):
            if name == "jupyter":
                continue
            servers.append({
                "name": name,
                "description": describe_server(sconf),
                "enabled": name in enabled,
                "required": False,
            })

        self.finish(json.dumps({"servers": servers}))

    @tornado.web.authenticated
    def post(self):
        cfg = self.settings["jclaude_config"]
        try:
            body = json.loads(self.request.body)
        except json.JSONDecodeError:
            self.set_status(400)
            self.finish(json.dumps({"error": "invalid JSON body"}))
            return

        enabled = body.get("enabled")
        if not isinstance(enabled, list) or not all(
            isinstance(x, str) for x in enabled
        ):
            self.set_status(400)
            self.finish(json.dumps({"error": "body must be {enabled: [str]}"}))
            return

        if "jupyter" not in enabled:
            enabled = ["jupyter", *enabled]

        cfg.enabled_mcp_servers = enabled
        self.log.info("jupyter_claude MCP servers set to: %s", enabled)
        self.finish(json.dumps({"enabled": list(cfg.enabled_mcp_servers)}))


def build_route_handlers(web_app):
    base_url = web_app.settings["base_url"]
    return [
        (url_path_join(base_url, "jupyter-claude", "hello"), HelloRouteHandler),
        (url_path_join(base_url, "jupyter-claude", "chat"), ChatWebSocketHandler),
        (url_path_join(base_url, "jupyter-claude", "mcp-servers"), McpServersHandler),
    ]


def setup_route_handlers(web_app):
    web_app.add_handlers(".*$", build_route_handlers(web_app))

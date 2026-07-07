import json

import tornado
from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join

from .chat_handler import ChatWebSocketHandler


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


def build_route_handlers(web_app):
    base_url = web_app.settings["base_url"]
    return [
        (url_path_join(base_url, "jupyter-claude", "hello"), HelloRouteHandler),
        (url_path_join(base_url, "jupyter-claude", "chat"), ChatWebSocketHandler),
    ]


def setup_route_handlers(web_app):
    web_app.add_handlers(".*$", build_route_handlers(web_app))

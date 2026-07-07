try:
    from ._version import __version__
except ImportError:
    import warnings
    warnings.warn("Importing 'jupyter_claude' outside a proper installation.")
    __version__ = "dev"

from .config import ClaudeExtensionApp


def _jupyter_labextension_paths():
    return [{"src": "labextension", "dest": "@dckartasoft/jupyter-claude"}]


def _jupyter_server_extension_points():
    return [{"module": "jupyter_claude", "app": ClaudeExtensionApp}]

import json

import pytest

from jupyter_claude.config import ClaudeExtensionApp


@pytest.fixture
def models_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("JUPYTER_CONFIG_DIR", str(tmp_path))
    return tmp_path


def _init(**traits):
    app = ClaudeExtensionApp()
    for k, v in traits.items():
        setattr(app, k, v)
    app.settings = {}
    app.initialize_settings()
    return app


def test_default_tiers_exclude_fable(models_dir):
    app = _init()
    assert app.allowed_tiers() == ["opus", "sonnet", "haiku"]


def test_json_tiers_filter_and_validate(models_dir):
    (models_dir / "jupyter_claude_models.json").write_text(
        json.dumps({"tiers": ["haiku", "fable", "bogus"]})
    )
    app = _init()
    assert app.allowed_tiers() == ["fable", "haiku"]
    # default main tier (sonnet) is not allowed -> falls back to haiku, not fable
    assert app.main_model_tier == "haiku"


def test_empty_tiers_fall_back_to_default(models_dir):
    (models_dir / "jupyter_claude_models.json").write_text(json.dumps({"tiers": []}))
    assert _init().allowed_tiers() == ["opus", "sonnet", "haiku"]


def test_json_overrides_trait_tiers(models_dir):
    (models_dir / "jupyter_claude_models.json").write_text(json.dumps({"tiers": ["opus"]}))
    app = _init(available_tiers=["haiku"])
    assert app.allowed_tiers() == ["opus"]


def test_tier_models_includes_fable(models_dir):
    assert _init().tier_models()["fable"].startswith("us.anthropic.claude-fable")

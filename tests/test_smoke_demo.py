"""Smoke tests for bootstrap and configuration."""

import os

import pytest

from ch04_eval import __version__
from ch04_eval.config import Settings, get_settings


def test_package_version():
    """Verify package version is set."""
    assert __version__ == "0.1.0"


def test_settings_defaults():
    """Verify settings provide valid defaults without crashing."""
    settings = Settings(
        ollama_api_key=None,
        opik_api_key=None,
        _env_file=None,
    )
    assert settings.ollama_base_url == "https://api.ollama.com"
    assert settings.opik_project_name == "ch04-debugging-hallucinations-math"
    assert not settings.has_ollama_key()
    assert not settings.has_opik_key()


def test_settings_validation_raises_when_missing():
    """Verify explicit validation raises descriptive error when key is missing."""
    settings = Settings(
        ollama_api_key=None,
        opik_api_key=None,
        _env_file=None,
    )
    with pytest.raises(ValueError, match="OLLAMA_API_KEY is required"):
        settings.validate_ollama()

    with pytest.raises(ValueError, match="OPIK_API_KEY is required"):
        settings.validate_opik()


def test_settings_cached_singleton():
    """Verify get_settings returns a cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_env_example_contains_all_settings():
    """Verify .env.example contains the expected environment keys."""
    env_example_path = ".env.example"
    assert os.path.exists(env_example_path)
    with open(env_example_path, "r", encoding="utf-8") as f:
        content = f.read()

    expected_keys = [
        "OLLAMA_API_KEY",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "OLLAMA_JUDGE_MODEL",
        "OPIK_API_KEY",
        "OPIK_PROJECT_NAME",
        "LOG_LEVEL",
    ]
    for key in expected_keys:
        assert key in content, f"Missing {key} in .env.example"

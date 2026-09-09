"""Tests for complexity → model routing."""

from unittest.mock import patch

import config
from agents.model_router import assign_model


def test_assign_model_default_trivial_uses_ollama(monkeypatch):
    monkeypatch.setattr(config, "JIRA_MODEL_ROUTING_JSON", "")
    with patch("agents.model_router._provider_available", return_value=True):
        with patch("agents.model_router.resolve_ollama_model", return_value="llama3.2:latest"):
            result = assign_model("trivial")
    assert result["provider"] == "ollama"
    assert result["tier"] == "trivial"
    assert "complexity:trivial" in result["routing_reason"]


def test_assign_model_exclude_local_removes_ollama(monkeypatch):
    monkeypatch.setattr(config, "JIRA_MODEL_ROUTING_JSON", "")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    with patch("agents.model_router._provider_available", return_value=True):
        result = assign_model("trivial", exclude_local=True)
    assert result["provider"] != "ollama"
    assert "no_local" in result["routing_reason"]


def test_assign_model_respects_custom_routing_json(monkeypatch):
    monkeypatch.setattr(
        config,
        "JIRA_MODEL_ROUTING_JSON",
        '{"trivial":{"provider":"anthropic","model":"claude-haiku-4-5"}}',
    )
    with patch("agents.model_router._provider_available", return_value=True):
        result = assign_model("trivial")
    assert result["provider"] == "anthropic"
    assert result["model"] == "claude-haiku-4-5"

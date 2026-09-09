"""Map ticket complexity tiers to provider + model choices."""

from __future__ import annotations

import json
from typing import Dict, Tuple

import config
from models.providers import ollama_list_models, resolve_ollama_model
from models.coding_agents import pick_best_installed


DEFAULT_ROUTING: Dict[str, Dict[str, str]] = {
    "trivial": {"provider": "ollama", "model": "llama3.2:latest"},
    "simple": {"provider": "ollama", "model": "codestral:latest"},
    "medium": {"provider": "anthropic", "model": "claude-haiku-4-5"},
    "complex": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
    "critical": {"provider": "openai", "model": "o3"},
}

# Used when local/Ollama models are excluded from poll assignment.
NO_LOCAL_ROUTING: Dict[str, Dict[str, str]] = {
    "trivial": {"provider": "anthropic", "model": "claude-haiku-4-5"},
    "simple": {"provider": "anthropic", "model": "claude-haiku-4-5"},
    "medium": {"provider": "anthropic", "model": "claude-haiku-4-5"},
    "complex": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
    "critical": {"provider": "openai", "model": "o3"},
}


def _routing_table() -> Dict[str, Dict[str, str]]:
    if config.JIRA_MODEL_ROUTING_JSON:
        try:
            custom = json.loads(config.JIRA_MODEL_ROUTING_JSON)
            merged = {**DEFAULT_ROUTING, **custom}
            return merged
        except json.JSONDecodeError:
            pass
    return DEFAULT_ROUTING


def _provider_available(provider: str) -> bool:
    if provider == "openai":
        return bool(config.OPENAI_API_KEY)
    if provider == "anthropic":
        return bool(config.ANTHROPIC_API_KEY)
    if provider == "gemini":
        return bool(config.GOOGLE_API_KEY)
    if provider == "cursor":
        return config.CURSOR_MODELS_ENABLED
    if provider == "ollama":
        return True
    return False


def _fallback_for_provider(provider: str, *, exclude_local: bool = False) -> Tuple[str, str]:
    """Pick a working provider/model when preferred is unavailable."""
    if config.ANTHROPIC_API_KEY:
        return "anthropic", config.ANTHROPIC_MODEL or "claude-sonnet-4-6"
    if config.OPENAI_API_KEY:
        return "openai", config.OPENAI_MODEL or "gpt-5.6"
    if config.CURSOR_MODELS_ENABLED:
        return "cursor", "composer-2.5"
    if exclude_local:
        raise RuntimeError(
            "No cloud model provider configured (Anthropic, OpenAI, or Cursor required when excluding local models)"
        )
    best = pick_best_installed(ollama_list_models())
    model = best or config.OLLAMA_MODEL or "codestral:latest"
    try:
        model = resolve_ollama_model(model, allow_fallback=True)
    except RuntimeError:
        pass
    return "ollama", model


def _choice_for_tier(tier: str, *, exclude_local: bool = False) -> Dict[str, str]:
    table = _routing_table()
    if exclude_local:
        base = NO_LOCAL_ROUTING.get(tier) or NO_LOCAL_ROUTING["medium"]
        routed = dict(table.get(tier) or table["medium"])
        if routed.get("provider") == "ollama":
            return dict(base)
        return routed
    return dict(table.get(tier) or table["medium"])


def assign_model(tier: str, *, exclude_local: bool = False) -> Dict[str, str]:
    """
    Return {provider, model, tier, routing_reason} for a complexity tier.
    Falls back when API keys or Ollama tags are missing.
    """
    choice = _choice_for_tier(tier, exclude_local=exclude_local)
    provider = choice.get("provider", "ollama")
    model = choice.get("model", config.OLLAMA_MODEL)

    reason = f"complexity:{tier}"
    if exclude_local:
        reason = f"{reason};no_local"

    if exclude_local and provider == "ollama":
        cloud = _choice_for_tier(tier, exclude_local=True)
        provider = cloud.get("provider", "anthropic")
        model = cloud.get("model", config.ANTHROPIC_MODEL)
        reason = f"{reason};remapped"

    if not _provider_available(provider):
        provider, model = _fallback_for_provider(provider, exclude_local=exclude_local)
        reason = f"{reason};fallback:{provider}"

    if provider == "ollama" and not exclude_local:
        try:
            model = resolve_ollama_model(model, allow_fallback=True)
        except RuntimeError:
            provider, model = _fallback_for_provider("ollama", exclude_local=exclude_local)
            reason = f"{reason};ollama_missing"
    elif provider == "ollama" and exclude_local:
        provider, model = _fallback_for_provider("ollama", exclude_local=True)
        reason = f"{reason};forced_cloud"

    return {
        "provider": provider,
        "model": model,
        "tier": tier,
        "routing_reason": reason,
    }

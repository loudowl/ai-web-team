"""
Curated model choices for the New Project UI — not tied to .env defaults alone.
"""

from typing import Dict, List, Optional

import config
from models.coding_agents import is_excluded_model, pick_best_installed
from models.providers import ollama_list_models


def _mark_default(models: List[dict], default_id: str) -> List[dict]:
    out = []
    for m in models:
        row = dict(m)
        row["default"] = row["id"] == default_id
        out.append(row)
    return out


OPENAI_MODELS: List[dict] = [
    {
        "id": "gpt-5.6",
        "display": "GPT-5.6",
        "tier": "frontier",
        "description": "Latest flagship reasoning model",
        "selectable": True,
    },
    {
        "id": "o3",
        "display": "o3",
        "tier": "frontier",
        "description": "Deep reasoning for complex engineering tasks",
        "selectable": True,
    },
    {
        "id": "gpt-5.5-medium",
        "display": "GPT-5.5",
        "tier": "frontier",
        "description": "Strong balance of speed and capability",
        "selectable": True,
    },
    {
        "id": "gpt-5.3-codex",
        "display": "GPT-5.3 Codex",
        "tier": "recent",
        "description": "Code-specialized; great for implementation",
        "selectable": True,
    },
    {
        "id": "gpt-5-mini",
        "display": "GPT-5 Mini",
        "tier": "recent",
        "description": "Fast, cost-efficient for lighter tasks",
        "selectable": True,
    },
]

ANTHROPIC_MODELS: List[dict] = [
    {
        "id": "claude-opus-4-8",
        "display": "Claude Opus 4.8",
        "tier": "frontier",
        "description": "Highest capability for hard problems",
        "selectable": True,
    },
    {
        "id": "claude-sonnet-4-6",
        "display": "Claude Sonnet 4.6",
        "tier": "frontier",
        "description": "Best balance of speed and quality",
        "selectable": True,
    },
    {
        "id": "claude-sonnet-4-5",
        "display": "Claude Sonnet 4.5",
        "tier": "recent",
        "description": "Previous Sonnet generation",
        "selectable": True,
    },
    {
        "id": "claude-haiku-4-5",
        "display": "Claude Haiku 4.5",
        "tier": "recent",
        "description": "Fast responses for simpler tasks",
        "selectable": True,
    },
]

# Top 10 local coding models — Chinese vendors shown but not selectable (enterprise policy)
OLLAMA_CODING_MODELS: List[dict] = [
    {
        "id": "codestral:latest",
        "display": "Codestral",
        "tier": "coding",
        "description": "Purpose-built coding model (Mistral)",
        "vendor": "Mistral AI",
        "params": "22B",
        "ram_hint": "~16 GB RAM",
        "license": "Mistral license",
        "strengths": ["Multi-file edits", "Refactors", "Jira tickets"],
        "pull": "ollama pull codestral",
        "selectable": True,
    },
    {
        "id": "devstral:latest",
        "display": "Devstral",
        "tier": "coding",
        "description": "Agentic repo editing (Mistral)",
        "vendor": "Mistral AI",
        "params": "24B",
        "ram_hint": "~16 GB RAM",
        "license": "Apache 2.0",
        "strengths": ["Agentic workflows", "Repo-wide changes", "Tool use"],
        "pull": "ollama pull devstral",
        "selectable": True,
    },
    {
        "id": "llama3.3:70b",
        "display": "Llama 3.3 70B",
        "tier": "coding",
        "description": "Strong general + code reasoning (Meta)",
        "vendor": "Meta",
        "params": "70B",
        "ram_hint": "~48 GB RAM (quantized ~40 GB)",
        "license": "Llama 3.3 Community",
        "strengths": ["Hard bugs", "Architecture", "Long context"],
        "pull": "ollama pull llama3.3:70b",
        "selectable": True,
    },
    {
        "id": "codellama:13b",
        "display": "Code Llama 13B",
        "tier": "coding",
        "description": "Solid open coding baseline (Meta)",
        "vendor": "Meta",
        "params": "13B",
        "ram_hint": "~10 GB RAM",
        "license": "Llama 2 Community",
        "strengths": ["Fill-in-middle", "Snippets", "Lower VRAM"],
        "pull": "ollama pull codellama:13b",
        "selectable": True,
    },
    {
        "id": "mixtral:8x7b",
        "display": "Mixtral 8x7B",
        "tier": "coding",
        "description": "MoE model for complex tasks (Mistral)",
        "vendor": "Mistral AI",
        "params": "8×7B MoE",
        "ram_hint": "~26 GB RAM",
        "license": "Apache 2.0",
        "strengths": ["Complex reasoning", "Large refactors"],
        "pull": "ollama pull mixtral:8x7b",
        "selectable": True,
    },
    {
        "id": "starcoder2:7b",
        "display": "StarCoder2 7B",
        "tier": "coding",
        "description": "Code-specialized (BigCode)",
        "vendor": "BigCode / Hugging Face",
        "params": "7B",
        "ram_hint": "~6 GB RAM",
        "license": "BigCode Open RAIL-M",
        "strengths": ["Code completion", "Many languages", "Lightweight"],
        "pull": "ollama pull starcoder2:7b",
        "selectable": True,
    },
    {
        "id": "granite-code:8b",
        "display": "Granite Code 8B",
        "tier": "coding",
        "description": "Enterprise-friendly Apache license (IBM)",
        "vendor": "IBM",
        "params": "8B",
        "ram_hint": "~6 GB RAM",
        "license": "Apache 2.0",
        "strengths": ["Enterprise policy", "Java / backend", "Low latency"],
        "pull": "ollama pull granite-code:8b",
        "selectable": True,
    },
    {
        "id": "llama3.2:3b",
        "display": "Llama 3.2 3B",
        "tier": "coding",
        "description": "Fast local default (Meta)",
        "vendor": "Meta",
        "params": "3B",
        "ram_hint": "~3 GB RAM",
        "license": "Llama 3.2 Community",
        "strengths": ["Speed", "Laptops", "Quick iterations"],
        "pull": "ollama pull llama3.2:3b",
        "selectable": True,
    },
    {
        "id": "qwen2.5-coder:7b",
        "display": "Qwen2.5 Coder 7B",
        "tier": "excluded",
        "description": "China-headquartered vendor — not permitted",
        "vendor": "Alibaba",
        "params": "7B (also 14B, 32B)",
        "ram_hint": "~6 GB RAM",
        "license": "Qwen license",
        "strengths": ["Strong coder (policy blocked)"],
        "pull": "Not permitted",
        "selectable": False,
        "excluded": True,
        "reason": "Enterprise policy: China-headquartered vendor",
    },
    {
        "id": "deepseek-coder-v2:16b",
        "display": "DeepSeek Coder V2",
        "tier": "excluded",
        "description": "China-headquartered vendor — not permitted",
        "vendor": "DeepSeek",
        "params": "16B (also 236B)",
        "ram_hint": "~12 GB RAM",
        "license": "DeepSeek license",
        "strengths": ["Strong coder (policy blocked)"],
        "pull": "Not permitted",
        "selectable": False,
        "excluded": True,
        "reason": "Enterprise policy: China-headquartered vendor",
    },
]

TIER_LABELS = {
    "frontier": "Frontier",
    "recent": "Recent releases",
    "coding": "Coding models",
    "excluded": "Restricted (not selectable)",
}

DEFAULT_MODEL_RAM_BYTES = 16 * 1024 ** 3


def models_match(a: str, b: str) -> bool:
    """True when two Ollama model tags refer to the same base model."""
    if not a or not b:
        return False
    a_norm, b_norm = a.lower(), b.lower()
    a_base, b_base = a_norm.split(":")[0], b_norm.split(":")[0]
    return a_norm == b_norm or a_base == b_base or a_norm.startswith(b_base + ":") or b_norm.startswith(a_base + ":")


def parse_ram_hint_bytes(ram_hint: str) -> int:
    """Parse catalog strings like '~16 GB RAM' into bytes."""
    if not ram_hint:
        return 0
    import re

    match = re.search(r"~?\s*(\d+(?:\.\d+)?)\s*GB", ram_hint, re.I)
    if not match:
        return 0
    return int(float(match.group(1)) * 1e9)


def lookup_model_display(model_name: str) -> str:
    for row in OLLAMA_CODING_MODELS:
        if models_match(row["id"], model_name):
            return row["display"]
    return (model_name or "model").split(":")[0]


def estimate_model_ram_bytes(model_name: str, running: Optional[List[dict]] = None) -> int:
    """Estimate RAM/VRAM for one concurrent agent run on the given model."""
    running = running or []
    for row in running:
        if models_match(row.get("name", ""), model_name):
            vram = row.get("vram_bytes") or row.get("size_bytes") or 0
            if vram:
                return int(vram)

    for row in ollama_list_models():
        if models_match(row.get("name", ""), model_name):
            size = row.get("size") or 0
            if size:
                return int(size * 0.75)

    for row in OLLAMA_CODING_MODELS:
        if models_match(row["id"], model_name):
            hint_bytes = parse_ram_hint_bytes(row.get("ram_hint", ""))
            if hint_bytes:
                return hint_bytes

    return DEFAULT_MODEL_RAM_BYTES


def _find_installed_variant(model_id: str, ollama_models: List[dict]) -> Optional[dict]:
    """Return the best-matching installed Ollama tag for a catalog id."""
    target = model_id.lower()
    base = target.split(":")[0]
    matches = []
    for m in ollama_models:
        name = (m.get("name") or "").lower()
        if name == target or name.startswith(base + ":") or name == base:
            matches.append(m)
    if not matches:
        return None
    matches.sort(key=lambda x: x.get("size") or 0, reverse=True)
    return matches[0]


def _format_size_gb(size_bytes: int) -> str:
    if not size_bytes:
        return ""
    return f"{size_bytes / 1e9:.1f} GB on disk"


def _build_ollama_tooltip(row: dict, installed: Optional[dict] = None) -> dict:
    """Structured tooltip payload for the New Project UI."""
    lines = []
    if row.get("vendor"):
        lines.append(f"Vendor: {row['vendor']}")
    if row.get("params"):
        lines.append(f"Parameters: {row['params']}")
    if row.get("ram_hint"):
        lines.append(f"Memory: {row['ram_hint']}")
    if row.get("license"):
        lines.append(f"License: {row['license']}")
    strengths = row.get("strengths") or []
    if strengths:
        lines.append(f"Best for: {', '.join(strengths)}")
    if installed:
        tag = installed.get("name", "")
        size = _format_size_gb(installed.get("size") or 0)
        lines.append(f"Installed as: {tag}" + (f" ({size})" if size else ""))
    elif row.get("selectable", True):
        lines.append("Status: Not installed locally")
        if row.get("pull"):
            lines.append(f"Install: {row['pull']}")
    if not row.get("selectable", True) and row.get("reason"):
        lines.append(f"Policy: {row['reason']}")
    return {
        "lines": lines,
        "pull": row.get("pull") if row.get("selectable", True) else None,
    }


def _ollama_is_installed(model_id: str, installed: set) -> bool:
    base = model_id.split(":")[0].lower()
    return any(name == model_id.lower() or name.startswith(base + ":") or name == base for name in installed)


def get_ollama_choices() -> List[dict]:
    ollama_models = ollama_list_models()
    installed_names = {(m.get("name") or "").lower() for m in ollama_models}
    choices = []
    for m in OLLAMA_CODING_MODELS:
        row = dict(m)
        variant = _find_installed_variant(row["id"], ollama_models)
        row["installed"] = _ollama_is_installed(row["id"], installed_names) if row.get("selectable") else False
        if variant:
            row["installed_tag"] = variant.get("name")
            row["installed_size_gb"] = round((variant.get("size") or 0) / 1e9, 1)
        row["tooltip"] = _build_ollama_tooltip(row, variant)
        choices.append(row)
    return choices


def get_provider_choices() -> dict:
    """Return curated model lists + availability for the New Project UI."""
    ollama_installed = ollama_list_models()
    best_installed = pick_best_installed(ollama_installed)

    openai_default = config.OPENAI_MODEL
    anthropic_default = config.ANTHROPIC_MODEL
    ollama_default = config.SENIOR_DEV_MODEL or config.OLLAMA_MODEL or best_installed or "codestral:latest"

    # Prefer env default when it matches a catalog entry; else first selectable
    def pick_default(catalog: List[dict], env_default: str) -> str:
        ids = {m["id"] for m in catalog if m.get("selectable", True)}
        if env_default in ids:
            return env_default
        base = env_default.split(":")[0]
        for m in catalog:
            if m.get("selectable", True) and m["id"].split(":")[0] == base:
                return m["id"]
        for m in catalog:
            if m.get("selectable", True):
                return m["id"]
        return catalog[0]["id"]

    ollama_default = pick_default(OLLAMA_CODING_MODELS, ollama_default)

    return {
        "tier_labels": TIER_LABELS,
        "providers": {
            "openai": {
                "available": bool(config.OPENAI_API_KEY),
                "default": pick_default(OPENAI_MODELS, openai_default),
                "models": _mark_default(OPENAI_MODELS, pick_default(OPENAI_MODELS, openai_default)),
            },
            "anthropic": {
                "available": bool(config.ANTHROPIC_API_KEY),
                "default": pick_default(ANTHROPIC_MODELS, anthropic_default),
                "models": _mark_default(ANTHROPIC_MODELS, pick_default(ANTHROPIC_MODELS, anthropic_default)),
            },
            "ollama": {
                "available": True,
                "default": ollama_default,
                "best_installed": best_installed,
                "models": _mark_default(get_ollama_choices(), ollama_default),
            },
        },
    }


def validate_model_choice(provider: str, model: str) -> Optional[str]:
    """Return error message if model is invalid; None if OK."""
    if not model:
        return None
    choices = get_provider_choices()["providers"].get(provider, {})
    catalog = {m["id"]: m for m in choices.get("models", [])}
    entry = catalog.get(model)
    if not entry:
        # Allow env-configured models not in catalog (advanced users)
        if provider == "ollama" and is_excluded_model(model):
            return f"Model '{model}' is restricted by enterprise policy"
        return None
    if not entry.get("selectable", True):
        return entry.get("reason") or f"Model '{model}' is not selectable"
    return None

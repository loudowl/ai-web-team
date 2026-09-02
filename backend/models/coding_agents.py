"""
Curated catalog of competitive open-weights coding models for local Ollama use.
Excludes models from vendors headquartered in China (per product policy).
"""

from typing import List, Dict, Optional
import re

# Vendors / model families to exclude (China-headquartered)
_EXCLUDED_PATTERNS = re.compile(
    r"(?i)(qwen|deepseek|yi-|chatglm|glm-|baichuan|internlm|codegeex|"
    r"minicpm|wizardcoder-cn|phind-code|starcode2?-zh)",
)

# Recommended open-weights coding models (competitive as of 2025–2026)
# `ollama_name` is the pull tag; may differ from display name.
RECOMMENDED_CODING_MODELS: List[Dict] = [
    {
        "id": "qwen2.5-coder",
        "display": "Qwen2.5 Coder",
        "ollama_name": "qwen2.5-coder",
        "vendor": "Alibaba",
        "excluded": True,
        "reason": "China-headquartered vendor",
        "params": ["7b", "14b", "32b"],
        "notes": "Strong coder but excluded by policy",
    },
    {
        "id": "deepseek-coder-v2",
        "display": "DeepSeek Coder V2",
        "ollama_name": "deepseek-coder-v2",
        "vendor": "DeepSeek",
        "excluded": True,
        "reason": "China-headquartered vendor",
        "params": ["16b", "236b"],
        "notes": "Excluded by policy",
    },
    {
        "id": "codellama",
        "display": "Code Llama",
        "ollama_name": "codellama",
        "vendor": "Meta",
        "excluded": False,
        "params": ["7b", "13b", "34b", "70b"],
        "notes": "Solid baseline; Meta open weights",
    },
    {
        "id": "llama3.3",
        "display": "Llama 3.3",
        "ollama_name": "llama3.3",
        "vendor": "Meta",
        "excluded": False,
        "params": ["70b"],
        "notes": "General + code; strong reasoning",
    },
    {
        "id": "llama3.2",
        "display": "Llama 3.2",
        "ollama_name": "llama3.2",
        "vendor": "Meta",
        "excluded": False,
        "params": ["1b", "3b"],
        "notes": "Fast local default",
    },
    {
        "id": "mistral",
        "display": "Mistral",
        "ollama_name": "mistral",
        "vendor": "Mistral AI",
        "excluded": False,
        "params": ["7b"],
        "notes": "Efficient European open weights",
    },
    {
        "id": "mixtral",
        "display": "Mixtral 8x7B",
        "ollama_name": "mixtral",
        "vendor": "Mistral AI",
        "excluded": False,
        "params": ["8x7b"],
        "notes": "MoE; good for complex tasks",
    },
    {
        "id": "codestral",
        "display": "Codestral",
        "ollama_name": "codestral",
        "vendor": "Mistral AI",
        "excluded": False,
        "params": ["22b"],
        "notes": "Purpose-built coding model",
    },
    {
        "id": "devstral",
        "display": "Devstral",
        "ollama_name": "devstral",
        "vendor": "Mistral AI",
        "excluded": False,
        "params": ["24b"],
        "notes": "Agentic coding / repo editing",
    },
    {
        "id": "granite-code",
        "display": "Granite Code",
        "ollama_name": "granite-code",
        "vendor": "IBM",
        "excluded": False,
        "params": ["8b", "20b", "34b"],
        "notes": "Enterprise-friendly Apache license",
    },
    {
        "id": "starcoder2",
        "display": "StarCoder2",
        "ollama_name": "starcoder2",
        "vendor": "BigCode",
        "excluded": False,
        "params": ["3b", "7b", "15b"],
        "notes": "Code-specialized; permissive license",
    },
    {
        "id": "phi4",
        "display": "Phi-4",
        "ollama_name": "phi4",
        "vendor": "Microsoft",
        "excluded": False,
        "params": ["14b"],
        "notes": "Small but capable reasoning",
    },
    {
        "id": "qwen3",
        "display": "Qwen3",
        "ollama_name": "qwen3",
        "vendor": "Alibaba",
        "excluded": True,
        "reason": "China-headquartered vendor",
        "params": ["8b", "14b", "32b"],
        "notes": "Excluded by policy",
    },
]


def is_excluded_model(name: str) -> bool:
    return bool(_EXCLUDED_PATTERNS.search(name or ""))


def get_recommended_models(include_excluded: bool = False) -> List[Dict]:
    if include_excluded:
        return RECOMMENDED_CODING_MODELS
    return [m for m in RECOMMENDED_CODING_MODELS if not m.get("excluded")]


def get_excluded_models() -> List[Dict]:
    return [m for m in RECOMMENDED_CODING_MODELS if m.get("excluded")]


def pick_best_installed(ollama_models: List[dict]) -> Optional[str]:
    """Pick the best non-excluded installed model for coding."""
    installed = {
        (m.get("name") or "").split(":")[0].lower()
        for m in ollama_models
    }
    for rec in get_recommended_models():
        base = rec["ollama_name"].lower()
        if base in installed:
            # prefer largest variant if multiple tags exist
            variants = [m.get("name") for m in ollama_models if m.get("name", "").startswith(base)]
            if variants:
                return variants[0]
    # Fallback: first installed non-excluded
    for m in ollama_models:
        name = m.get("name", "")
        if name and not is_excluded_model(name):
            return name
    return None

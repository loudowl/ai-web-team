"""Central configuration — reads from environment / .env file."""

import os
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Model providers ────────────────────────────────────────────────────────────
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
OLLAMA_BASE_URL    = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Default model per provider
OPENAI_MODEL       = os.getenv("OPENAI_MODEL", "gpt-4o")
ANTHROPIC_MODEL    = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
OLLAMA_MODEL       = os.getenv("OLLAMA_MODEL", "llama3.2")

# Per-agent model overrides (optional — falls back to provider defaults)
AGENT_MODELS = {
    "pm":         os.getenv("PM_MODEL",         ""),
    "designer":   os.getenv("DESIGNER_MODEL",   ""),
    "architect":  os.getenv("ARCHITECT_MODEL",  ""),
    "developer":  os.getenv("DEVELOPER_MODEL",  ""),
}

# Default provider: "openai" | "anthropic" | "ollama"
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "openai")

# ── GitHub ─────────────────────────────────────────────────────────────────────
GITHUB_TOKEN       = os.getenv("GITHUB_TOKEN", "")
GITHUB_USERNAME    = os.getenv("GITHUB_USERNAME", "")

# ── App ────────────────────────────────────────────────────────────────────────
DB_PATH            = os.getenv("DB_PATH", "data/projects.db")
MAX_TOKENS_AGENT   = int(os.getenv("MAX_TOKENS_AGENT", "4096"))

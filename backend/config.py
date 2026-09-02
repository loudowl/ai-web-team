"""Central configuration — reads from environment / .env file."""

import os
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Model providers ────────────────────────────────────────────────────────────
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
OLLAMA_BASE_URL    = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Default model per provider. OpenAI defaults to a current reasoning-capable
# model; override per-deployment via env if your key targets a different model.
OPENAI_MODEL       = os.getenv("OPENAI_MODEL", "gpt-5.6")
ANTHROPIC_MODEL    = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
OLLAMA_MODEL       = os.getenv("OLLAMA_MODEL", "llama3.2")

# Per-agent model overrides (optional — falls back to provider defaults)
AGENT_MODELS = {
    "pm":         os.getenv("PM_MODEL",         ""),
    "designer":   os.getenv("DESIGNER_MODEL",   ""),
    "architect":  os.getenv("ARCHITECT_MODEL",  ""),
    "developer":  os.getenv("DEVELOPER_MODEL",  ""),
    "senior_dev": os.getenv("SENIOR_DEV_MODEL", ""),
}

# Per-agent reasoning effort for OpenAI reasoning models (Responses API).
# The hardest tasks — architecture and code generation — get more thinking
# budget; planning/design stay lighter to control cost and latency.
AGENT_REASONING_EFFORT = {
    "pm":         os.getenv("PM_EFFORT",        "low"),
    "designer":   os.getenv("DESIGNER_EFFORT",  "medium"),
    "architect":  os.getenv("ARCHITECT_EFFORT", "high"),
    "developer":  os.getenv("DEVELOPER_EFFORT", "high"),
    "senior_dev": os.getenv("SENIOR_DEV_EFFORT", "high"),
}

# Default provider: "openai" | "anthropic" | "ollama"
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "openai")

# ── Jira Mode ─────────────────────────────────────────────────────────────────
JIRA_BASE_URL      = os.getenv("JIRA_BASE_URL", "")          # e.g. https://yourorg.atlassian.net
JIRA_EMAIL         = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN     = os.getenv("JIRA_API_TOKEN", "")

# Local git worktrees for parallel ticket work (one dir per project/ticket)
WORKTREE_BASE        = os.getenv("WORKTREE_BASE", "data/worktrees")
# Default repo context root when user does not pass one per project
REPO_CONTEXT_PATH    = os.getenv("REPO_CONTEXT_PATH", "")

# ── GitHub ─────────────────────────────────────────────────────────────────────
GITHUB_TOKEN       = os.getenv("GITHUB_TOKEN", "")
GITHUB_USERNAME    = os.getenv("GITHUB_USERNAME", "")

# ── App ────────────────────────────────────────────────────────────────────────
DB_PATH            = os.getenv("DB_PATH", "data/projects.db")
# Reasoning models spend hidden tokens before visible output, so give the
# response budget more headroom than the old chat-completions default.
MAX_TOKENS_AGENT   = int(os.getenv("MAX_TOKENS_AGENT", "8192"))

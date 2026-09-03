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
SENIOR_DEV_MODEL   = os.getenv("SENIOR_DEV_MODEL", "")
# Context window — each doubling roughly doubles RAM while a model is loaded.
# 8192 is fine for most Jira tickets; 32768 needs 32GB+ RAM with codestral.
OLLAMA_NUM_CTX     = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
# Unload model after idle ("0" = immediately after each request). Ollama duration string or seconds.
OLLAMA_KEEP_ALIVE  = os.getenv("OLLAMA_KEEP_ALIVE", "5m")
# Cap CPU threads for Ollama inference (empty = Ollama default).
OLLAMA_NUM_THREAD  = int(os.getenv("OLLAMA_NUM_THREAD", "0")) or None
# Jira tickets run in parallel by default on cloud APIs; keep local Ollama to one at a time.
JIRA_MAX_PARALLEL  = max(1, int(os.getenv("JIRA_MAX_PARALLEL", "1")))

# Per-agent model overrides (optional — falls back to provider defaults)
AGENT_MODELS = {
    "pm":         os.getenv("PM_MODEL",         ""),
    "designer":   os.getenv("DESIGNER_MODEL",   ""),
    "architect":  os.getenv("ARCHITECT_MODEL",  ""),
    "developer":  os.getenv("DEVELOPER_MODEL",  ""),
    "senior_dev": SENIOR_DEV_MODEL,
    "code_reviewer": os.getenv("CODE_REVIEW_MODEL", "") or SENIOR_DEV_MODEL,
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
    "code_reviewer": os.getenv("CODE_REVIEW_EFFORT", "medium"),
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

# Jira PR workflow
GITHUB_BASE_BRANCH   = os.getenv("GITHUB_BASE_BRANCH", "")   # auto-detect from origin if empty
JIRA_COLLAB_BRANCH_PREFIX = os.getenv("JIRA_COLLAB_BRANCH_PREFIX", "collab/release")
JIRA_BRANCH_PREFIX   = os.getenv("JIRA_BRANCH_PREFIX", "codex")
JIRA_BRANCH_SUFFIX   = os.getenv("JIRA_BRANCH_SUFFIX", "")

# Lint + PR review workflow (Jira mode)
JIRA_LINT_ENABLED        = os.getenv("JIRA_LINT_ENABLED", "true").lower() in ("1", "true", "yes")
JIRA_LINT_COMMAND        = os.getenv("JIRA_LINT_COMMAND", "npm run lint")
JIRA_LINT_FIX_COMMAND    = os.getenv("JIRA_LINT_FIX_COMMAND", "npm run lint:fix")
JIRA_LINT_MAX_ROUNDS     = max(1, int(os.getenv("JIRA_LINT_MAX_ROUNDS", "2")))
JIRA_COPILOT_REVIEW      = os.getenv("JIRA_COPILOT_REVIEW", "true").lower() in ("1", "true", "yes")
JIRA_COPILOT_WAIT_SEC    = max(0, int(os.getenv("JIRA_COPILOT_WAIT_SEC", "90")))
JIRA_COPILOT_MAX_ROUNDS  = max(1, int(os.getenv("JIRA_COPILOT_MAX_ROUNDS", "1")))

# ── GitHub ─────────────────────────────────────────────────────────────────────
GITHUB_TOKEN       = os.getenv("GITHUB_TOKEN", "")
GITHUB_USERNAME    = os.getenv("GITHUB_USERNAME", "")

# ── App ────────────────────────────────────────────────────────────────────────
DB_PATH            = os.getenv("DB_PATH", "data/projects.db")
PORT               = int(os.getenv("PORT", "3001"))
# Uvicorn auto-reload when started via `python main.py` (disable during Jira runs).
RELOAD             = os.getenv("RELOAD", "true").lower() in ("1", "true", "yes")
# Reasoning models spend hidden tokens before visible output, so give the
# response budget more headroom than the old chat-completions default.
MAX_TOKENS_AGENT   = int(os.getenv("MAX_TOKENS_AGENT", "8192"))

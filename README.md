# ai-web-team

A multi-agent AI system for two workflows:

1. **Greenfield** — turn a plain-English brief into a scaffolded web app (PM → Designer → Architect → Developer).
2. **Jira mode** — run a senior coding agent per ticket against a real repo: plan, implement, lint, open PRs, and track work on a swim board.

Watch agents work in real time via the **web UI** (primary) or the **Expo mobile app**.

![React](https://img.shields.io/badge/Web-React%20%2B%20Vite-61DAFB?logo=react&logoColor=white)
![React Native](https://img.shields.io/badge/Mobile-Expo-000020?logo=expo&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-black)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-Claude-CC785C)

Repo: [github.com/loudowl/ai-web-team](https://github.com/loudowl/ai-web-team)

---

## Modes

### Greenfield (4-agent pipeline)

| Agent | Role | Output |
|---|---|---|
| 📋 **Project Manager** | Brief → structured PRD | Requirements, user stories, priorities |
| 🎨 **Designer** | PRD → design brief | Palette, typography, layouts |
| 🏗️ **Architect** | PRD + design → architecture | Stack, folders, API contracts |
| 💻 **Developer** | All above → code | Runnable implementation |

Each agent receives prior agents' output as context. When finished, push to a new GitHub repo from the UI.

### Jira mode (ticket swim board)

A **senior_dev** agent runs per ticket in isolated git worktrees:

- Fetch ticket from Jira (or paste key / URL / manual text)
- Gather repo context, analyze, implement, apply patches
- Run lint fix loop (optional)
- Commit, push, open PR
- Address Copilot review (optional, workflow-dependent)

**Board lanes:** To Do → In Progress → In Review → Dev Complete

**Workflows per ticket:**

| Workflow | Lint | Copilot review |
|---|---|---|
| Simple fix | ✓ | ✓ |
| Fix | ✓ | — |
| Full cycle | ✓ | ✓ (extended wait) |

**Collab branches:** Jira fix versions map to `collab/release-{version}` (prefix configurable) for worktree base and PR target.

---

## Web UI

The web app (`web/`) is the main interface:

- **Dashboard** — stats, Jira batches, greenfield sessions, quick actions
- **Global nav** — Home · New Jira project · Jira board · Settings
- **Jira board** (`/board`) — all non-archived tickets across batches in one swim board
- **Per-batch board** (`/board/:projectId`) — tickets for one batch
- **Ollama memory meter** — RAM budget as tickets move to In Progress
- **Model pull modal** — if an assigned Ollama model is missing, download it in-app with progress, then auto-start the run
- **Demo mode** — sample swim board without backend

Floating **+** on the dashboard opens a new greenfield project. **Jira ticket** / **Greenfield** buttons launch the corresponding new-project flows.

---

## Mobile UI

The Expo app (`mobile/`) provides:

- **Kanban board** — four greenfield agents with live status
- **Activity feed** — streaming tokens and events
- **Settings** — Ollama model list, pull progress, delete

Use your machine's LAN IP in `EXPO_PUBLIC_API_URL` when testing on a physical device.

---

## Setup

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in keys + Jira/repo paths for Jira mode
python main.py
```

API default: `http://localhost:3001`

### Web

```bash
cd web
npm install
npm run dev
```

UI default: `http://localhost:5173`

Optional `web/.env`:

```
VITE_API_URL=http://localhost:3001
```

### Mobile

```bash
cd mobile
npm install
cp .env.example .env
npx expo start
```

---

## Configuration

### Backend `.env` (highlights)

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` / `OPENAI_MODEL` | OpenAI via Responses API |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | Claude |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | Local Ollama (default port 11434) |
| `DEFAULT_PROVIDER` | `openai` · `anthropic` · `ollama` |
| `GITHUB_TOKEN` / `GITHUB_USERNAME` | Push greenfield projects + Jira PRs |
| `JIRA_BASE_URL` / `JIRA_EMAIL` / `JIRA_API_TOKEN` | Jira API (optional; paste works too) |
| `REPO_CONTEXT_PATH` | Path to target repo for Jira worktrees |
| `JIRA_COLLAB_BRANCH_PREFIX` | e.g. `collab/release` → `collab/release-11.5.0` |
| `SENIOR_DEV_MODEL` | Override coding model for Jira runs |
| `JIRA_MAX_PARALLEL` | Concurrent ticket runs (default 1 for Ollama) |
| `OLLAMA_NUM_CTX` / `OLLAMA_KEEP_ALIVE` | Tune local RAM / unload behavior |
| `RELOAD` | Set `false` during long Jira runs to avoid uvicorn reload |

See `backend/.env.example` for lint, Copilot review, and per-agent overrides.

At least one LLM provider must be configured. For Jira mode with Ollama, pull a coding model first (e.g. `ollama pull codestral`) or use the in-app download prompt.

### Mobile `.env`

```
EXPO_PUBLIC_API_URL=http://YOUR_MACHINE_IP:3001
```

---

## Model manager

From **Settings** (web or mobile):

- List installed Ollama models and sizes
- Pull models with live progress (SSE)
- Delete models
- Memory meter (web board) estimates concurrent ticket RAM

Recommended local coding models: **codestral**, **devstral**, **qwen2.5-coder**, **deepseek-coder-v2**.

---

## Architecture

```
ai-web-team/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py              SQLite: projects, tickets, agent runs
│   ├── agents/
│   │   ├── runner.py            Greenfield pipeline
│   │   ├── jira_runner.py       Per-ticket Jira agent + board replay
│   │   └── prompts.py
│   ├── models/
│   │   ├── providers.py         OpenAI / Anthropic / Ollama streaming
│   │   ├── model_catalog.py     Curated model picker metadata
│   │   └── coding_agents.py
│   ├── routes/
│   │   ├── projects.py
│   │   ├── board.py             Per-project board API (run, archive, lanes)
│   │   ├── board_global.py      All-tickets board API
│   │   ├── models.py            Ollama pull / check / memory
│   │   └── ws.py                WebSocket events
│   └── utils/
│       ├── git_worktree.py
│       ├── github_pr.py
│       ├── jira_client.py
│       ├── collab_branch.py
│       ├── lint_runner.py
│       └── repo_context.py
├── web/                         Vite + React dashboard & swim board
└── mobile/                      Expo client
```

---

## Stack

- **Backend:** Python 3.11+ · FastAPI · WebSockets · SQLite
- **Web:** React 18 · Vite · React Router · Zustand · Lucide
- **Mobile:** React Native · Expo · Zustand
- **LLMs:** OpenAI · Anthropic · Ollama
- **Git:** worktrees, GitHub PR API, optional Contents API push (greenfield)

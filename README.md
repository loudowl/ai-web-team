# ai-web-team

A multi-agent AI system that turns a plain-English project brief into a fully scaffolded web app — with a mobile interface to watch it happen in real time.

Describe what you want to build. Four specialized AI agents collaborate, each building on the last's output. When they're done, push the result directly to a new GitHub repo.

![React Native](https://img.shields.io/badge/React_Native-Expo-000020?logo=expo&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-black)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-Claude-CC785C)

---

## The Agent Team

| Agent | Role | Output |
|---|---|---|
| 📋 **Project Manager** | Translates brief → structured PRD | Requirements, user stories, priorities |
| 🎨 **Designer** | PRD → design brief | Color palette, typography, component list, screen layouts |
| 🏗️ **Architect** | PRD + design → tech architecture | Stack decisions, folder structure, API contracts, data models |
| 💻 **Developer** | All above → working code | Complete, runnable implementation files |

Each agent receives the previous agents' output as context, building a coherent system rather than working in isolation.

---

## Mobile UI

The app combines two views:

**Kanban board** — top strip showing all 4 agents as cards. Each card shows the agent's current status (Waiting / Working / Done), a pulsing border when active, and a preview of their output. Tap any card to read the full output.

**Activity feed** — scrolling chat-style log showing each agent event as it arrives, with live streaming tokens from the active agent rendered in real time with a blinking cursor.

---

## Setup

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python main.py
```

### Mobile

```bash
cd mobile
npm install
cp .env.example .env
npx expo start
```

Scan the QR code with Expo Go, or press `i` for iOS simulator / `a` for Android.

---

## Configuration

### Backend `.env`

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Optional | GPT-4o access |
| `ANTHROPIC_API_KEY` | Optional | Claude access |
| `OLLAMA_BASE_URL` | Optional | Ollama server (default: localhost:11434) |
| `OLLAMA_MODEL` | Optional | Default Ollama model (default: llama3.2) |
| `DEFAULT_PROVIDER` | Optional | `openai` / `anthropic` / `ollama` |
| `GITHUB_TOKEN` | Optional | For push-to-GitHub feature |
| `GITHUB_USERNAME` | Optional | Your GitHub username |

At least one LLM provider must be configured. Ollama requires `llama3.2` or similar to be pulled locally.

### Mobile `.env`

```
EXPO_PUBLIC_API_URL=http://YOUR_MACHINE_IP:3001
```

Use your machine's local IP (not `localhost`) when running on a physical device.

---

## Model Manager

The Settings screen lets you manage Ollama models directly from the app:
- View all installed models with file sizes
- Pull new models (with live progress bar)
- Delete models you no longer need

---

## Architecture

```
ai-web-team/
├── backend/
│   ├── main.py                 FastAPI entry point
│   ├── config.py               Environment config
│   ├── database.py             SQLite (projects, agent runs, artifacts)
│   ├── agents/
│   │   ├── runner.py           Pipeline orchestrator + WebSocket streaming
│   │   └── prompts.py          System prompts + prompt builders per agent
│   ├── models/
│   │   └── providers.py        OpenAI / Anthropic / Ollama streaming
│   ├── routes/
│   │   ├── projects.py         REST: CRUD + GitHub push
│   │   ├── models.py           REST: Ollama model management
│   │   └── ws.py               WebSocket: real-time pipeline events
│   └── utils/
│       └── github_push.py      GitHub Contents API integration
└── mobile/
    ├── App.js                  Navigation root
    └── src/
        ├── screens/
        │   ├── HomeScreen.js       Project list
        │   ├── NewProjectScreen.js  Brief input + provider selection
        │   ├── ProjectScreen.js     Kanban + activity feed + actions
        │   └── SettingsScreen.js    Model manager + config
        ├── components/
        │   ├── AgentKanban.js       4-agent status board
        │   └── ActivityFeed.js      Streaming chat-style event log
        ├── store/
        │   └── projectStore.js      Zustand state (agents, feed, WS)
        └── services/
            └── api.js               Axios + WebSocket client
```

---

## Stack

- **Backend**: Python 3.11 · FastAPI · WebSockets · SQLite
- **LLMs**: OpenAI GPT-4o · Anthropic Claude · Ollama (local)
- **Mobile**: React Native · Expo · Zustand · react-native-markdown-display
- **GitHub integration**: GitHub Contents API (no git binary required)

# Jira board auto-ingest & Pre assessed lane

General-purpose Jira integration for any Atlassian Cloud site. Configure `JIRA_BASE_URL`, credentials, project key, and board id — no org-specific defaults are required.

## Goal

Poll a Jira board’s **To Do** issues, mirror them on a local swim board, triage tickets without a fix version in **Pre assessed**, and assign coding models before anyone runs a workflow.

## Swim board lanes

| Lane | Purpose |
|---|---|
| **Pre assessed** | Tickets with **no fix version** in Jira — grouped by inferred fix version and collapsible **Rec size** (XS–XL) sub-groups |
| **To Do** | Groomed tickets ready for model/workflow selection |
| **In Progress** | Agent runs |
| **In Review** | PR opened |
| **Dev Complete** | Manual completion |

## Pre assessed features

- **Fix version inference** — reads project fix versions from Jira API; matches title/description/labels; priority-aware unreleased version selection (no env default)
- **T-shirt size recommendation** — story points or complexity tier rubric; shown in red as **Rec size** when not set in Jira
- **Fix version badges** — green **Fix version** when assigned; red **Rec fix version** when inferred
- **Ticket modal** — Jira link, size reasoning (content-specific), **Questions for the ticket creator**, recommended fix version
- **Properties modal** — set fix version, t-shirt size, provider/model before moving to To Do
- **Drag & drop** — Pre assessed ↔ To Do; sync refreshes existing tickets from Jira (fix version, lane, grooming fields)

## Jira poll

| Mode | API | Behavior |
|---|---|---|
| **Sync now** | `POST /api/jira-poll/projects/{id}/sync` | Fetch To Do + ingest new + **update existing** |
| **Reset board** | `POST /api/jira-poll/projects/{id}/reset` | Delete all local tickets, re-import from Jira |
| **Start polling** | `POST /api/jira-poll/projects/{id}/start` | Background loop |
| **Stop** | `POST /api/jira-poll/projects/{id}/stop` | Cancel loop |

Requires `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`.

Optional env:

- `JIRA_BOARD_ID` — agile board id from board URL
- `JIRA_PROJECT_KEY` — e.g. `PROJ`
- `JIRA_TODO_JQL` — override To Do query
- `JIRA_TSHIRT_SIZE_FIELD` — custom field id for t-shirt size
- `JIRA_MODEL_ROUTING_JSON` — tier → `{provider, model}` map
- `JIRA_POLL_INTERVAL_SEC` — default 300

## Complexity & model routing

Heuristic scoring at ingest (no LLM call — fast, deterministic):

| Tier | Signals | Default routing |
|---|---|---|
| trivial | Short text, no AC | Local / small cloud model |
| simple | Moderate scope | Local or Haiku-class |
| medium | Longer AC, labels | Haiku / mini |
| complex | Epic keywords, long spec | Sonnet-class |
| critical | Architecture/refactor language | Strongest available model |

**No local models** checkbox excludes Ollama from poll assignment and can reassign existing To Do tickets to cloud providers.

## Database (tickets)

Grooming columns: `jira_priority`, `t_shirt_size`, `recommended_t_shirt_size`, `recommended_t_shirt_size_reason`, `recommended_fix_version`, `creator_questions_json`, `board_lane` (`pre_assessed`, …).

## Follow-ups

- [ ] Gemini / Cursor execution bridges
- [ ] Optional LLM-based triage (`JIRA_COMPLEXITY_LLM`)
- [ ] Bidirectional Jira column sync
- [ ] Push grooming fields back to Jira

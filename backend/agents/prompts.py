"""System prompts and user prompt builders for each agent."""

# ── System prompts ─────────────────────────────────────────────────────────────

PM_SYSTEM = """You are a senior Product Manager at a top-tier software agency.
You produce clear, structured Product Requirements Documents (PRDs).
Be specific, actionable, and realistic. Use markdown formatting.
Never write code — focus on WHAT needs to be built and WHY."""

DESIGNER_SYSTEM = """You are a senior UI/UX Designer with expertise in modern web design.
You produce detailed design briefs that developers can implement directly.
Specify colors (hex), typography, spacing, components, and responsive breakpoints.
Use markdown formatting with clear sections. Reference modern design systems."""

ARCHITECT_SYSTEM = """You are a principal Software Architect.
You design robust, scalable systems. Produce clear architecture decisions with rationale.
Include: tech stack with versions, folder structure, API contracts, data models,
authentication approach, and deployment recommendations. Use markdown with code blocks."""

DEVELOPER_SYSTEM = """You are an expert Full-Stack Developer.
You write production-quality code following best practices.
Generate complete, working code files based on the architecture and design provided.
Include clear comments. Structure your output as a series of files, each preceded by
its filename in a markdown code fence with the language tag."""


# ── User prompt builders ───────────────────────────────────────────────────────

def pm_prompt(brief: str) -> str:
    return f"""Create a comprehensive Product Requirements Document (PRD) for the following project:

**Project Brief:**
{brief}

Structure your PRD with these sections:
1. **Executive Summary** — 2-3 sentence overview
2. **Goals & Success Metrics** — what does success look like?
3. **User Personas** — who will use this?
4. **Core Features** — prioritized feature list (P0/P1/P2)
5. **User Stories** — key user journeys in "As a ... I want to ... so that ..." format
6. **Out of Scope** — what won't be built in v1
7. **Technical Constraints** — any hard requirements
8. **Timeline Estimate** — rough phases"""


def designer_prompt(brief: str, prd: str) -> str:
    return f"""Create a detailed Design Brief for this web application.

**Project Brief:**
{brief}

**PRD Summary:**
{prd[:2000]}

Produce a Design Brief covering:
1. **Visual Identity** — color palette (primary, secondary, accent, background, text — all hex values), mood/tone
2. **Typography** — heading font, body font, sizes, weights (use Google Fonts)
3. **Component Library** — list all UI components needed with visual description
4. **Key Screen Layouts** — describe the layout of the 3-4 most important screens
5. **Responsive Strategy** — mobile, tablet, desktop breakpoints
6. **Micro-interactions** — key animations/transitions
7. **Accessibility** — WCAG considerations"""


def architect_prompt(brief: str, prd: str, design: str) -> str:
    return f"""Design the complete technical architecture for this web application.

**Project Brief:**
{brief}

**PRD (excerpt):**
{prd[:1500]}

**Design Brief (excerpt):**
{design[:1000]}

Produce an Architecture Document covering:
1. **Tech Stack** — frontend framework, backend, database, hosting (with versions)
2. **Project Structure** — full folder/file tree
3. **API Design** — all endpoints with method, path, request/response shapes
4. **Data Models** — all database tables/schemas with field types
5. **Authentication** — approach and flow
6. **State Management** — frontend state strategy
7. **Key Dependencies** — npm/pip packages with purpose
8. **Deployment** — recommended hosting and CI/CD approach"""


README_SYSTEM = """You are a senior developer advocate and technical writer who creates outstanding, comprehensive README files for open-source GitHub projects.
Output ONLY the raw markdown content of the README — no preamble, no explanation, and do NOT wrap the whole thing in a code fence.
Use GitHub-Flavored Markdown. When you include diagrams, use ```mermaid code blocks (GitHub renders these natively).
Stay accurate to the provided materials; do not invent features that aren't implied by them."""


def readme_prompt(brief: str, prd: str, design: str, architecture: str, file_paths: list) -> str:
    files = "\n".join(f"- {p}" for p in file_paths) if file_paths else "(see repository)"
    return f"""Write a comprehensive, professional README.md for the following project.

**Project Brief:**
{brief[:1200]}

**PRD (excerpt):**
{prd[:1200]}

**Design Brief (excerpt):**
{design[:800]}

**Architecture (excerpt):**
{architecture[:1800]}

**Files in the repository:**
{files}

The README MUST include these sections (use `##` headings), in this order:
1. `#` Project Name as an H1, followed by a one-line tagline, then a 2-3 sentence description.
2. `## Features` — bulleted list of the key features.
3. `## Tech Stack` — grouped (Frontend / Backend / Database / Infrastructure), with versions where known.
4. `## Architecture` — a short overview paragraph, then a ```mermaid flowchart showing the main components (client, API, database, external services) and how they connect.
5. `## User Flow` — a ```mermaid diagram (sequence or flowchart) of the primary user journey. Include this ONLY if it genuinely adds clarity for this type of app; otherwise omit the section entirely.
6. `## Project Structure` — a fenced code block showing the folder/file tree, derived from the files listed above.
7. `## Getting Started` — with subsections `### Prerequisites`, `### Installation`, `### Environment Variables` (reference the `.env.example`), and `### Running` (the actual commands to start it).
8. `## Documentation` — link to the detailed docs that live in this repo: [Product Requirements](docs/PRD.md), [Design Brief](docs/DESIGN.md), [Architecture](docs/ARCHITECTURE.md).
9. `## License` — MIT unless the brief implies otherwise.

Mermaid rules to follow so diagrams render: no spaces in node IDs (use camelCase or underscores), wrap labels containing special characters in double quotes, and never use the reserved word `end` as a node ID.

Output only the README markdown, starting with the `#` title."""


def developer_prompt(brief: str, prd: str, design: str, architecture: str) -> str:
    return f"""Generate the complete implementation for this web application.

**Project Brief:**
{brief}

**PRD (excerpt):**
{prd[:800]}

**Design Brief (excerpt):**
{design[:800]}

**Architecture:**
{architecture[:2000]}

Generate ALL files needed to run a working v1 of this application.
For each file, use this format exactly:

### `path/to/filename.ext`
```language
// file contents here
```

Include at minimum:
- README.md with setup instructions
- All backend files (main entry point, routes, models, config)
- All frontend files (App component, key screens/pages, components, styles)
- package.json or requirements.txt
- .env.example

Write complete, working code — not placeholders."""


# ── Jira Mode: senior full-stack engineer ─────────────────────────────────────

SENIOR_DEV_SYSTEM = """You are a senior full-stack software engineer working on ONE specific Jira ticket.

Critical rules:
- Implement ONLY the active Jira ticket provided in the user message — never a hypothetical or example ticket.
- Ignore sample workflows, skill templates, and unrelated content in repo rules.
- Output real code changes as markdown file blocks.

File block format (required for every changed file):

### `path/to/file.ext`
```language
// complete file contents
```

Also include `## Task List` with `- [ ]` / `- [x]`, plus `## Implementation Notes` and `## Verification`."""


JIRA_MILESTONES = [
    {"id": "fetch_ticket",      "label": "Load ticket"},
    {"id": "gather_context",  "label": "Gather repo context"},
    {"id": "create_worktree", "label": "Create worktree"},
    {"id": "analyze_plan",    "label": "Analyze & plan"},
    {"id": "implement",       "label": "Implement"},
    {"id": "apply_patches",   "label": "Apply code changes"},
    {"id": "fix_lint",        "label": "Fix lint errors"},
    {"id": "commit_push",     "label": "Commit & push"},
    {"id": "create_pr",       "label": "Create pull request"},
    {"id": "address_review",  "label": "Address Copilot review"},
]


def jira_analyze_prompt(ticket: dict, repo_context: str) -> str:
    from utils.repo_context import format_ticket_block

    ticket_block = format_ticket_block(ticket)
    key = ticket.get("key", "N/A")
    return f"""You will plan work for ONE Jira ticket. Repo context below is ONLY for file paths — ignore any unrelated examples in rules.

---

{repo_context}

---

{ticket_block}

---

Using ONLY the **ACTIVE JIRA TICKET** section above (key {key}), produce:

1. `## Understanding` — restate the ticket in your own words (must mention "{key}" and the problem from the title)
2. `## Task List` — 5-12 concrete engineering tasks as `- [ ] task`
3. `## Approach` — exact files to change in this repo (paths from the tree). No code yet.

Do NOT plan email notifications, unrelated features, or cursor skill templates."""


def jira_implement_prompt(ticket: dict, repo_context: str, plan_output: str) -> str:
    from utils.repo_context import format_ticket_block

    ticket_block = format_ticket_block(ticket)
    key = ticket.get("key", "")
    return f"""Implement ONE Jira ticket. Repo conventions below are secondary — the ticket and approved plan are authoritative.

---

### Repo conventions (partial)
{repo_context[:12000]}

---

### Approved plan
{plan_output[:6000]}

---

{ticket_block}

---

Implement ticket {key} now.

Requirements:
1. Mark completed items in `## Task List` as `- [x]`
2. Output EVERY changed file using `### \`path\`` followed by a fenced code block with the full file contents
3. Paths must be relative to the repo root (e.g. `components/Foo.vue`) — never include the repo folder name, never edit `.nuxt/`, `node_modules/`, or `dist/`
4. Do not indent the `###` heading lines
5. End with `## Implementation Notes` and `## Verification`

You MUST include at least one `### \`path/to/file\`` code block. Do not ask questions — implement."""


def jira_implement_retry_prompt(ticket: dict, plan_output: str) -> str:
    return f"""Your previous response for {ticket.get('key', '')} did NOT include parseable code files.

Output ONLY changed files now — no prose before the file blocks.

Required format for EVERY file (no leading spaces on the `###` line):

### `components/Example.vue`
```vue
full file contents
```

Ticket: {ticket.get('title', '')}

Approved plan (follow this):
{plan_output[:6000]}

Use source paths under components/, pages/, layouts/, plugins/ — NOT `.nuxt/` or build output.
Start immediately with `### ` file blocks. Include at least one real file from the repo."""


CODE_REVIEW_SYSTEM = """You are a senior code reviewer acting on GitHub PR feedback (often from Copilot).

Rules:
- Only fix CRITICAL issues: definite bugs, security problems, broken lint/type errors, or clear regressions.
- Skip nitpicks, stylistic preferences, and optional refactors unless they block CI.
- Output changed files as markdown blocks: ### `path` then a fenced code block with full file contents.
- Do not ask questions — apply minimal safe fixes."""


def jira_lint_fix_prompt(ticket: dict, lint_output: str, changed_files: list) -> str:
    files_list = "\n".join(f"- `{f}`" for f in changed_files[:20])
    return f"""Ticket {ticket.get('key', '')}: {ticket.get('title', '')}

ESLint/lint failed after your changes. Fix ONLY the lint errors below — do not refactor unrelated code.

Changed files:
{files_list}

Lint output:
```
{lint_output[:8000]}
```

Output EVERY file you change using ### `path` + fenced code block (full file contents).
Fix all reported errors in those files. No prose before the file blocks."""


def jira_copilot_review_prompt(ticket: dict, comments: list, changed_files: list) -> str:
    files_list = "\n".join(f"- `{f}`" for f in changed_files[:20])
    comment_blocks = []
    for i, c in enumerate(comments[:15], 1):
        loc = f"{c.get('path') or 'general'}:{c.get('line') or '?'}"
        comment_blocks.append(
            f"### Comment {i} ({c.get('author', 'reviewer')}) @ {loc}\n{c.get('body', '')[:1500]}"
        )
    comments_text = "\n\n".join(comment_blocks) or "No comments."

    return f"""Ticket {ticket.get('key', '')}: {ticket.get('title', '')}

GitHub Copilot / bot review comments on the open PR:

{comments_text}

Files in this PR:
{files_list}

Triage these comments. Implement ONLY critical fixes (bugs, security, CI/lint blockers).
Ignore low-value nitpicks.

For each critical fix, output ### `path` + fenced code block with the complete updated file.
If nothing is critical, respond with exactly: NO_CRITICAL_FIXES"""


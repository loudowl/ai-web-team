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

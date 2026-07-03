# Project History

This document records the development journey of AgentCommit. Every completed feature, architectural decision, and milestone should be logged here in chronological order.

---

## Project Information

**Project:** AgentCommit

**Started:** YYYY-MM-DD

**Status:** 🚧 In Development

---

# Timeline

## YYYY-MM-DD — Project Initialization

### Completed
- Created project repository
- Added AGENTS.md
- Defined project architecture
- Selected technology stack

### Files Added
- README.md
- AGENTS.md
- PROJECT_HISTORY.md

### Decisions
- Frontend will use Next.js 15.
- Backend will use FastAPI.
- Google ADK will orchestrate all agents.
- GitHub OAuth chosen for authentication.

### Next Steps
- Initialize frontend
- Initialize backend
- Set up Google ADK

---

## 2026-07-03 — Phase 1 MVP Foundation

#### Completed
- Scaffolded Next.js 15 frontend with TypeScript, Tailwind CSS v4, shadcn/ui
- Scaffolded FastAPI backend with full project structure
- Created Docker Compose for PostgreSQL 16 + Redis 7
- Built premium landing page with 4 sections (Hero, Features, Architecture, CTA)
- Created Navbar (glassmorphism) and Footer components
- Built 5 AI agents with Google ADK (Coordinator, Profile, Repo, Issue, Explainer)
- Created GitHub API tool functions (ADK-compatible)
- Built Redis caching layer for agent responses
- Created SQLAlchemy database models (User, ProfileAnalysis, SavedIssue)
- Built FastAPI REST endpoints (auth, profile, repos, issues)
- Created typed API client for frontend-backend communication
- Integrated GitHub MCP server client
- Created comprehensive .gitignore, .env.example files
- Updated README.md with full documentation

#### Files Added
- `.gitignore`
- `.env.example`
- `docker-compose.yml`
- `frontend/` — Complete Next.js 15 app
  - `src/app/layout.tsx`, `src/app/page.tsx`, `src/app/globals.css`
  - `src/components/landing/hero.tsx`, `features.tsx`, `architecture.tsx`, `cta.tsx`
  - `src/components/shared/navbar.tsx`, `footer.tsx`, `github-icon.tsx`
  - `src/components/ui/` — shadcn components (button, card, badge, avatar, etc.)
  - `src/lib/api.ts`, `src/lib/utils.ts`
  - `src/types/index.ts`
  - `.env.example`
- `backend/` — Complete FastAPI app
  - `app/main.py`, `app/config.py`, `app/__init__.py`
  - `app/api/auth.py`, `profile.py`, `repos.py`, `issues.py`
  - `app/agents/coordinator.py`, `profile_agent.py`, `repo_agent.py`, `issue_agent.py`, `explainer_agent.py`
  - `app/tools/github_tool.py`, `utils.py`
  - `app/models/schemas.py`
  - `app/database/connection.py`, `models.py`
  - `app/mcp/__init__.py`
  - `requirements.txt`, `Dockerfile`, `.env.example`

#### Decisions
- PostgreSQL from the start (via Docker) instead of SQLite
- Redis caching included in Phase 1 with per-agent TTL strategy
- GitHub MCP integration included in Phase 1
- Dark mode as default theme with indigo/violet brand palette
- Custom GitHub SVG icon (lucide-react lacks brand icons)
- `http://localhost:3000` as the default frontend dev URL

#### Challenges
- lucide-react no longer exports a `Github` brand icon; resolved with custom SVG component

#### Notes
- Frontend build passes cleanly with zero TypeScript errors
- Backend requires `pip install -r requirements.txt` in a virtual environment
- Database services need Docker: `docker compose up -d`

#### Next Steps
- Set up GitHub OAuth credentials and test auth flow
- Connect frontend to backend API
- Build Dashboard page (protected route)
- Build Issue Detail page
- End-to-end testing of the agent pipeline
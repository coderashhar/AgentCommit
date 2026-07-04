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

---

## 2026-07-03 — GitHub OAuth + Dashboard + Issue Detail

#### Completed
- Implemented NextAuth.js v5 with GitHub OAuth provider
- Created auth session provider and middleware for protected routes
- Extended NextAuth types to expose GitHub access token in session
- Built auth-aware Navbar (sign-in/sign-out, user avatar, dashboard link)
- Updated Hero and CTA sections with real GitHub sign-in actions
- Built Dashboard page with full agent pipeline (profile → repos → issues)
- Created ProfileCard component (avatar, bio, stats)
- Created SkillBadges component (languages, frameworks, domains, experience level)
- Created RepoRecommendations component (match scores, stars, language badges)
- Created IssueList component (difficulty badges, labels, comments, relative time)
- Built Issue Detail page with AI explanation view
- Generated AUTH_SECRET for NextAuth

#### Files Added
- `frontend/src/lib/auth.ts` — NextAuth v5 configuration
- `frontend/src/types/next-auth.d.ts` — Session type augmentation
- `frontend/src/app/api/auth/[...nextauth]/route.ts` — OAuth route handler
- `frontend/src/middleware.ts` — Protected route middleware
- `frontend/src/components/providers.tsx` — SessionProvider wrapper
- `frontend/src/app/dashboard/page.tsx` — Dashboard page
- `frontend/src/app/issue/[...id]/page.tsx` — Issue detail page
- `frontend/src/components/dashboard/profile-card.tsx`
- `frontend/src/components/dashboard/skill-badges.tsx`
- `frontend/src/components/dashboard/repo-recommendations.tsx`
- `frontend/src/components/dashboard/issue-list.tsx`
- `frontend/.env.local` — Frontend environment variables

#### Files Modified
- `frontend/src/app/layout.tsx` — Added Providers wrapper
- `frontend/src/components/shared/navbar.tsx` — Auth-aware with avatar
- `frontend/src/components/landing/hero.tsx` — Real sign-in actions
- `frontend/src/components/landing/cta.tsx` — Real sign-in actions
- `frontend/src/components/landing/architecture.tsx` — Fixed arrow alignment

#### Decisions
- Used NextAuth v5 (Auth.js) with `AUTH_GITHUB_ID`/`AUTH_GITHUB_SECRET` env vars
- GitHub access token forwarded through JWT → session for backend API calls
- Dashboard runs a sequential agent pipeline: profile → repos → issues
- Issue detail uses catch-all route `[...id]` to handle `owner/repo/number` segments
- Middleware protects `/dashboard` and `/issue/*` routes

#### Notes
- Frontend build passes cleanly with zero TypeScript errors
- `useSession()` status in next-auth v5 beta doesn't include "loading" — use data checks instead
- Need to restart dev server after creating `.env.local`

#### Next Steps
- End-to-end testing with real GitHub OAuth flow
- Wire MCP tools into agents
- Add loading animations and error states

---

## 2026-07-05 — Backend Agent JSON Fallback Resilience

#### Completed
- Debugged the dashboard-facing `API error 500: Backend Error: Agent did not return valid JSON` failure path.
- Hardened ADK event response extraction to collect non-empty text from all event parts instead of relying only on the first final-response part.
- Added explicit empty-response handling before JSON parsing.
- Added GitHub API-backed fallback responses for profile analysis, repository recommendations, issue discovery, and issue explanation when an agent returns empty or invalid JSON.

#### Files Modified
- `backend/app/agents/coordinator.py`
- `PROJECT_HISTORY.md`

#### Decisions
- Preserved the agent-first flow so Gemini responses remain the preferred output.
- Used existing GitHub tool functions for fallback data rather than adding another integration layer.
- Kept API response schemas unchanged so the frontend dashboard and issue detail pages do not need changes.

#### Known Issues / Follow-up Tasks
- Full backend import smoke testing requires installing backend dependencies, including `google-adk`, in the local Python environment.

---

## 2026-07-05 — Backend 500 Hardening and Runtime Verification

#### Completed
- Created a Python 3.12 backend virtual environment at `backend/.venv312` and installed backend dependencies.
- Made Redis cache reads, writes, deletes, and malformed cached values fail open instead of crashing API requests.
- Added shared GitHub token validation helper for protected backend routes.
- Replaced repeated inline GitHub token checks in profile, repository, and issue endpoints.
- Verified the FastAPI app imports, route wiring works, degraded profile analysis works with Redis unavailable and empty agent output, and the health endpoint responds from a running server.

#### Files Added
- `backend/app/api/github_auth.py`

#### Files Modified
- `.gitignore`
- `backend/app/api/profile.py`
- `backend/app/api/repos.py`
- `backend/app/api/issues.py`
- `backend/app/tools/utils.py`
- `PROJECT_HISTORY.md`

#### Decisions
- Treat Redis as an optional cache dependency for request handling; unavailable cache should reduce performance, not break the dashboard.
- Keep GitHub auth validation centralized so future protected endpoints return consistent JSON errors.

#### Known Issues / Follow-up Tasks
- Real dashboard analysis still requires valid GitHub OAuth credentials and a reachable GitHub API.
- Gemini-powered agent responses require a valid Google API key; otherwise the GitHub-backed fallback path is used.

---

## 2026-07-05 - Frontend Runtime Repair and Verification

#### Completed
- Fixed the Auth.js `MissingSecret` crash that sent GitHub sign-in clicks to `/api/auth/error`.
- Added a local development auth secret fallback while keeping production dependent on a real `AUTH_SECRET`.
- Made GitHub sign-in buttons check provider availability and show a clear local setup alert when OAuth credentials are missing.
- Added a frontend `.env.example` and README setup note for Auth.js/GitHub OAuth variables.
- Restored the missing frontend library layer for API calls, Auth.js/NextAuth configuration, and shared UI/date/format helpers.
- Narrowed the Python `lib/` ignore rule so `frontend/src/lib` can be tracked by Git.
- Migrated the protected route boundary from deprecated `middleware.ts` to Next 16 `proxy.ts`.
- Fixed the dashboard React lint failure by deriving the session-backed profile instead of synchronously setting state in an effect.
- Fixed issue detail links so `owner/repo/number` routes are generated as real catch-all route segments.
- Removed stale unused imports from dashboard, issue detail, profile card, and repository recommendation components.
- Hardened protected backend endpoints so missing or malformed authorization headers return 401 instead of request-validation 422.
- Added an npm PostCSS override to clear the Next.js transitive audit finding without downgrading Next.

#### Files Added
- `frontend/.env.example`
- `frontend/src/lib/auth-client.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/auth.ts`
- `frontend/src/lib/utils.ts`
- `frontend/src/proxy.ts`

#### Files Modified
- `backend/app/api/github_auth.py`
- `backend/app/api/issues.py`
- `backend/app/api/profile.py`
- `backend/app/api/repos.py`
- `.gitignore`
- `README.md`
- `frontend/.gitignore`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/src/app/dashboard/page.tsx`
- `frontend/src/app/issue/[...id]/page.tsx`
- `frontend/src/components/dashboard/issue-list.tsx`
- `frontend/src/components/dashboard/profile-card.tsx`
- `frontend/src/components/dashboard/repo-recommendations.tsx`
- `frontend/src/components/landing/cta.tsx`
- `frontend/src/components/landing/hero.tsx`
- `frontend/src/components/shared/navbar.tsx`
- `frontend/src/lib/auth.ts`
- `PROJECT_HISTORY.md`

#### Files Removed
- `frontend/src/middleware.ts`

#### Verification
- `npm run lint`
- `npx tsc --noEmit`
- `npm run build`
- `npm audit --audit-level=moderate`
- `python -m compileall app`
- FastAPI health and missing-auth smoke tests

#### Known Issues / Follow-up Tasks
- Running the full authenticated dashboard still requires real GitHub OAuth credentials and a valid GitHub access token.

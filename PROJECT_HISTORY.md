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

## 2026-07-05 — Skill Analyzer and Repository Recommendation Fixes

*(Backfilled during Phase 1 stabilization — this entry was skipped when the commit
landed, in violation of AGENTS.md's history rule. Reconstructed from the commit diff.)*

#### Completed
- Substantial rework of `backend/app/agents/coordinator.py` (491 lines changed):
  profile, repo, and issue recommendation flows, plus GitHub-backed fallback paths.
- Added `backend/app/api/github_auth.py` usage across the issues/profile/repos routers.
- Built the Dashboard page's agent pipeline UI, ProfileCard, SkillBadges,
  RepoRecommendations, and IssueList components.
- Built the Issue Detail page with an AI-explanation view.
- Wired GitHub OAuth sign-in through the landing page's Hero/CTA sections and the
  auth-aware Navbar.

#### Files Added
- `frontend/src/app/dashboard/page.tsx`
- `frontend/src/app/issue/[...id]/page.tsx`
- `frontend/src/components/dashboard/profile-card.tsx`, `skill-badges.tsx`,
  `repo-recommendations.tsx`, `issue-list.tsx`
- `frontend/src/components/providers.tsx`
- `frontend/src/middleware.ts`
- `frontend/src/types/next-auth.d.ts`
- `backend/app/api/github_auth.py`

#### Files Modified
- `backend/app/agents/coordinator.py`, `explainer_agent.py`, `issue_agent.py`,
  `profile_agent.py`, `repo_agent.py`
- `backend/app/api/issues.py`, `profile.py`, `repos.py`
- `backend/app/config.py`, `backend/app/models/schemas.py`,
  `backend/app/tools/github_tool.py`, `backend/app/tools/utils.py`
- `frontend/src/app/layout.tsx`, `frontend/src/app/api/auth/[...nextauth]/route.ts`
- `frontend/src/components/landing/architecture.tsx`, `cta.tsx`, `hero.tsx`
- `frontend/src/components/shared/navbar.tsx`
- `frontend/next.config.ts`

#### Known Issues / Follow-up Tasks (discovered later, during Phase 1 stabilization)
- The repo/issue recommendation logic introduced here ranked by GitHub stars with a
  floor but no ceiling, and the LLM prompt told the model "well-starred repos (100+)
  indicate community trust" with no ceiling either — this surfaced as the dashboard
  recommending mega-repos (`microsoft/vscode`, `freeCodeCamp/freeCodeCamp`,
  `TheAlgorithms/*`) that are unrealistic first-contribution targets. Fixed in the
  entry below.
- The issue detail page's deep link (`issue-list.tsx`) encoded `owner/repo` as one
  URL segment while the detail page expected three, making every issue click produce
  a permanent loading spinner. Fixed in the entry below.
- The GitHub OAuth token was interpolated directly into Gemini prompt text on every
  agent call. Fixed in the entry below.

---

## 2026-08-29 — Phase 1 Stabilization: Tiered Recommendations, Security, PRD/Architecture

#### Completed
- Replaced star-ranked repository and issue recommendations with experience-tiered
  ranking: beginner/intermediate/advanced bands (star ceiling, activity window, repo
  size, labelled-issue thresholds) applied identically across the LLM path, LLM-output
  verification, and the deterministic fallback.
- Added a real repo/issue scoring model (`score_repo`, `score_issue`) replacing the
  previous positional `match_score` formula, and a three-way issue difficulty
  classifier (`classify_issue_difficulty`) replacing a two-way label-substring test
  that could never return "hard".
- Added LLM-output verification: every agent-proposed repository/issue is re-fetched
  from GitHub and rebuilt from ground truth (or dropped on 404/tier-ceiling failure)
  before reaching the frontend, closing the hallucination gap left by
  `extra="ignore"` + fully-defaulted Pydantic schemas.
- Removed the GitHub OAuth token from Gemini prompt text; agents are now built
  per-request via `build_*_agent(github_token)` factories that bind the token through
  a closure instead.
- Fixed the issue-detail deep link (dropped `encodeURIComponent` around
  `repo_full_name` so the catch-all route receives three segments, not one), and
  added a "not found" state for malformed issue URLs instead of an infinite spinner.
- Added a `next-auth` `authorized` callback so `middleware.ts` actually gates
  `/dashboard` and `/issue/*` — previously the default `authorized: true` meant the
  middleware matcher did nothing.
- Added real loading/empty/error states to the dashboard's three agent-fed panels
  (previously the error state left "still working" copy visible next to the error
  banner), a retry affordance that resets the pipeline, and `AbortController` +
  run-latch guards against React StrictMode double-invoking the (LLM-backed) pipeline.
- Added `logging.config.dictConfig` in `main.py` — no logger was ever configured
  before this, so every `logger.warning`/`logger.info` (including all Redis
  fail-open and agent-fallback messages) was silently discarded.
- Stopped echoing raw Python exception text to the browser from the four API routers;
  replaced `traceback.print_exc()` with `logger.exception(...)`.
- Fixed `.env.example` (root): `CORS_ORIGINS` was a bare string, which
  pydantic-settings fails to parse (`SettingsError`) since it JSON-parses list-typed
  settings — following the README's `cp .env.example .env` verbatim produced a
  backend that crashed on import. Reconciled stale `NEXTAUTH_*`/`GITHUB_CLIENT_*`
  names to the `AUTH_*` names NextAuth v5 actually reads.
- Made the frontend's backend-proxy target (`next.config.ts`) read from
  `BACKEND_API_URL` instead of a hardcoded `127.0.0.1:8000`, so a deployed frontend
  can point at a deployed backend.
- Added `PRD.md` and `ARCHITECTURE.md` at the repo root.

#### Files Added
- `backend/app/tools/repo_ranking.py` — pure tier bands, query builder, repo scorer
- `backend/app/tools/issue_ranking.py` — pure issue filters, difficulty classifier, scorer
- `PRD.md`, `ARCHITECTURE.md`

#### Files Modified
- `backend/app/agents/coordinator.py` (rewritten), `repo_agent.py`, `issue_agent.py`,
  `profile_agent.py`, `explainer_agent.py` (all converted to per-request factories)
- `backend/app/tools/github_tool.py` (search sort/order fix, `fetch_repo` added,
  request timeouts), `backend/app/tools/utils.py` (`build_cache_key`)
- `backend/app/models/schemas.py` (additive fields: `forks`, `pushed_at`, `tier`,
  `verified`, `source`, `updated_at`)
- `backend/app/main.py` (logging config), `backend/app/api/profile.py`, `repos.py`,
  `issues.py` (error-detail sanitization)
- `frontend/src/app/dashboard/page.tsx`, `frontend/src/app/issue/[...id]/page.tsx`
- `frontend/src/components/dashboard/issue-list.tsx`, `repo-recommendations.tsx`,
  `skill-badges.tsx`, `profile-card.tsx` (unused-import cleanup)
- `frontend/src/lib/auth.ts`, `frontend/src/lib/api.ts`, `frontend/src/types/index.ts`
- `frontend/next.config.ts`
- `.env.example`, `frontend/.env.example`

#### Decisions
- Tiered star ceilings (not a single global cutoff) so advanced users still see
  large, high-quality projects while beginners never see them — see `PRD.md` §4 and
  `ARCHITECTURE.md` §3.1 for the exact bands and rationale.
- LLM-path verification tops up rather than replaces the deterministic fallback when
  fewer than 5 repos (3 issues) survive, preserving the agent-first flow: the model's
  real picks stay ranked first, `source` becomes `"hybrid"` rather than discarding
  its output outright.
- Cache keys stay profile-scoped (not per-user) deliberately — the bug was missing
  input dimensions and caching empty results, not sharing itself. Bumped
  `CACHE_SCHEMA_VERSION` to `v2` so old entries age out on their own TTL rather than
  requiring a flush.
- Left PostgreSQL and GitHub MCP unwired — see `ARCHITECTURE.md` §5 for the explicit
  Phase 2 trigger conditions, so this isn't an open-ended deferral.

#### Known Issues / Follow-up Tasks
- No test harness exists anywhere in the repo. The new ranking modules are pure
  functions specifically so this is cheap to close in Phase 2 — see `PRD.md` §4 and
  `ARCHITECTURE.md` §7.
- `require_github_token` still costs a live GitHub round-trip, uncached, on every
  protected request.
- No rate limiting or request-size bounds (e.g. `IssueDiscoveryRequest.repositories`
  has no max length).
- Gemini free-tier 429 handling is mitigated (the deterministic fallback is now
  tier-correct) but not resolved — a request can still stall ~100s across 5 retries
  before falling through.

---

## 2026-09-03 — Niche-Language Recommendation Fix

#### Completed
- Diagnosed and fixed labelled-issue query starvation for small language ecosystems,
  found by running the tier queries against live GitHub rather than mocks.
- Split the relaxed pass's `good-first-issues` / `help-wanted-issues` qualifiers into
  separate unioned queries via a new `IssueQualifier` enum.
- Flattened `_search_tier_repos` into explicit ordered passes, removing the previous
  three-level nesting with three separate cap checks at different depths.
- Added 6 `IssueQualifier` query-builder tests and 3 `_search_tier_repos` escalation
  tests.

#### Files Modified
- `backend/app/tools/repo_ranking.py`
- `backend/app/agents/coordinator.py`
- `backend/tests/test_repo_ranking.py`
- `backend/tests/test_coordinator.py`
- `PROJECT_HISTORY.md`

#### Decisions
- Split the qualifiers rather than retuning the tier bands. GitHub search has no `OR`
  across qualifiers, and loosening the bands would have muddied attribution — the
  defect was conjoining two independent signals, not the bands being wrong.
- The star ceiling is still never relaxed in any pass, including the new split
  variants; a test asserts this for every `IssueQualifier` value.

#### Measurements (live GitHub, beginner tier, relaxed band)
- Elixir: 2 repositories conjoined → 14 unioned (`good-first-issues` alone 5,
  `help-wanted-issues` alone 11).
- Mainstream languages were already healthy and are unchanged: JavaScript 35,
  Python 105, TypeScript 55.

#### Known Issues / Follow-up Tasks
- **No CI exists.** `.github/workflows/` is absent, so the 193-test suite runs only
  locally and nothing gates a pull request.
- `_search_tier_repos` had no direct test coverage before this change — a missing
  import broke the real code path while every query-builder unit test still passed.
  Other coordinator search paths may have the same gap.
- End-to-end verification against real GitHub OAuth + Gemini is still unperformed;
  see `MANUAL_TESTS.md` (currently untracked).

---

## 2026-09-04 — Phase 2 Landed; Docs and Setup Reconciled

#### Completed
- Squash-merged PR #6 (`17ea434`), bringing CI, the orchestration tests, and the
  `/commit` Suspense fix onto `main`. Phase 2 had been complete and green since
  2 Sep but had never landed, so `main` still had no pipeline and a failing
  `next build`.
- Fixed Alembic: `alembic upgrade head` could not run in any configuration.
  `alembic/env.py` builds an **async** engine via `async_engine_from_config`, but
  `alembic.ini` configured the sync `postgresql://` driver — the command died on
  `No module named 'psycopg2'` (psycopg2 is not, and need not be, a dependency).
  `env.py` now normalizes `postgres://` / `postgresql://` onto `postgresql+asyncpg://`
  and defaults to `app.config.settings.database_url`, so `.env` is the single source
  of truth and `alembic.ini` no longer has to be hand-edited per environment.
- Rebuilt `backend/.venv` on Python 3.12 — it had been a Python 3.9 environment
  containing only pip and setuptools, so the suite ran locally only by accident,
  against a separate interpreter that happened to have the dependencies.
- Rewrote `ARCHITECTURE.md` §5 and §7, which still described the Phase 1 world:
  §5 asserted PostgreSQL and GitHub MCP were "fully unwired" (both have been wired
  since Phase 2) and §7 listed "no pytest, no CI anywhere in this repository" as a
  known risk, next to 237 passing tests and a working workflow.
- Added `ARCHITECTURE.md` §2.1, a table of all seven agent-backed routes with their
  coordinator function, cache TTL, and fallback. §2 previously documented only the
  profile flow, implying the three Phase 1 stages were the whole system.
- Tracked `MANUAL_TESTS.md`, which `PROJECT_HISTORY.md` already cited as the
  end-to-end checklist while it sat untracked in the working tree.

#### Files Modified
- `backend/alembic/env.py`, `backend/alembic.ini`
- `ARCHITECTURE.md` (§1 stack table, §2.1 added, §5 rewritten, §6 plan cache row,
  §7 rewritten, §7.1 added)
- `README.md` (Python 3.12 requirement, `alembic upgrade head` step, a test-running
  section, and the Next.js 16 / Gemini 2.5 Flash corrections)
- `MANUAL_TESTS.md` (newly tracked)

#### Decisions
- Normalized **toward** asyncpg rather than adding psycopg2 and a sync engine. The
  app is async end to end; adding a second driver to satisfy Alembic would mean two
  connection stacks and two failure modes for one migration command.
- Derived Alembic's default URL from `app.config.settings` instead of duplicating it
  in `alembic.ini`. The previous split meant a developer editing `.env` got an app
  and a migration runner pointed at different databases, silently.
- Left the README's aspirational architecture diagram alone but corrected the two
  factual stack claims. `ARCHITECTURE.md` §1 remains the place where divergence from
  the README is recorded deliberately.

#### Measurements
- `pytest`: 236 passed, 1 skipped (integration, needs live credentials) — 237
  collected. Previously 228 passed with 8 errors locally, because `aiosqlite` was
  absent from the interpreter the suite actually ran under.
- `alembic upgrade head` before the fix: `No module named 'psycopg2'` at engine
  construction. After: reaches asyncpg authentication against localhost:5432.

#### Known Issues / Follow-up Tasks
- **The migration is runnable but nothing runs it.** `lifespan` in `main.py` is still
  an empty placeholder and no release step invokes the upgrade. A fresh deployment
  comes up with no schema.
- `alembic upgrade head` has not been observed applying the revision to a real
  database — Docker was unavailable, and the native PostgreSQL on this machine has
  no `agentcommit` role. Verification stopped at "asyncpg connects and authenticates".
- `api/saved.py` still makes two `GET /user` calls per request and omits the
  empty-`login` guard on its GET and DELETE handlers — next up.

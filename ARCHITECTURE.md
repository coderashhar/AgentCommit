# AgentCommit — Architecture

**Status:** Describes the system as built after Phase 2, not as originally
envisioned. Where reality diverges from `README.md`/`ROADMAP.md`, this
document says so explicitly rather than silently matching the aspirational version.
**Companion doc:** `PRD.md` covers product scope and rationale; this document is the
technical design underneath it.

---

## 1. Stack, corrected

| Layer | README claims | Actual |
|---|---|---|
| Frontend | Next.js 15 | **Next.js 16.2.10**, React 19.2.4 |
| LLM | Gemini 2.5 Pro | **gemini-2.5-flash** |
| Backend | FastAPI, Python 3.12+ | Matches — FastAPI 0.115, Python 3.12 |
| AI framework | Google ADK | Matches |
| Database | PostgreSQL + Redis | Both live — Redis caches agent results, PostgreSQL stores profile analyses and saved issues (§5) |
| Auth | GitHub OAuth | NextAuth v5 (Auth.js), not the backend's own `/api/auth` router (§4) |

## 2. Request flow

```
Browser
  │
  │  POST /api/proxy/api/profile/analyze   (Next.js rewrite → FastAPI, same-origin)
  ▼
FastAPI router (app/api/profile.py)
  │  require_github_token()  — live GET api.github.com/user per request, no cache
  ▼
coordinator.run_profile_analysis()
  │
  ├─ cache_get(build_cache_key("profile", username))  — Redis, 1h TTL
  │
  ├─ (miss) build_profile_agent(token) → ADK Agent, tools bound via closure
  │         _run_agent() → Gemini, up to 5 retries on 429
  │         _parse_json_response() → ProfileAnalysisResponse
  │
  └─ (agent exception) _fallback_profile_analysis()
            → fetch_github_profile() + fetch_user_repos() directly, no LLM
```

The dashboard runs this **three times in sequence** — profile → repos → issues —
each stage's output feeding the next (`frontend/src/app/dashboard/page.tsx`). Repo
recommendation and issue discovery both follow the same shape as above, with one
addition specific to them: **LLM-path verification** (§3.3).

### 2.1 Agent entry points

Phase 2 added four more agent-backed routes on the same shape as above — cache
lookup, agent run, deterministic fallback. The full set:

| Route | Coordinator function | Cached | Fallback |
|---|---|---|---|
| `POST /api/profile/analyze` | `run_profile_analysis` | 1h | `_fallback_profile_analysis` |
| `POST /api/repos/recommend` | `run_repo_recommendation` | 30m | `_deterministic_repo_recommendation` |
| `POST /api/issues/discover` | `run_issue_discovery` | 15m | `_deterministic_issue_discovery` |
| `POST /api/issues/explain` | `run_issue_explanation` | 2h | `_fallback_issue_explanation` |
| `POST /api/issues/plan` | `run_implementation_plan` | 2h | `_fallback_implementation_plan` |
| `POST /api/mentor/chat` | `run_mentor_chat` | no — session-scoped | none — returns an explicit error |
| `POST /api/commit/generate` | `run_commit_message` | no | `_fallback_commit_message` |

The mentor is the one stateful flow: `agents/mentor_session.py` maps
`{username}:{owner}/{repo}#{issue}` to a live ADK `session_id` so follow-up
questions keep context. It deliberately has no fallback — a mentor that cannot
reach the model should say so rather than answer from a keyword heuristic.

`POST`, `GET`, and `DELETE /api/saved/issues` are the only routes that touch no
agent at all; they read and write PostgreSQL directly.

### 2.2 The `coordinator_agent` is dead code

`app/agents/coordinator.py` used to construct a root `Agent` with
`sub_agents=[profile_agent, repo_agent, issue_agent, explainer_agent]`, implying ADK
handles routing between them. **It never did** — every `run_*` function builds and
runs exactly one leaf agent directly. There is no multi-agent orchestration in this
codebase today, despite the module name and the architecture diagram in `README.md`.
This was removed during Phase 1 stabilization along with the token-in-prompt fix,
since both touched the same agent-construction code path (§4).

## 3. Recommendation ranking (Phase 1's core rework)

### 3.1 The tier model

`backend/app/tools/repo_ranking.py` defines `ExperienceTier` (beginner /
intermediate / advanced, derived from the profile agent's `experience_level` output)
and a `TierBand` per tier: hard star bounds (floor **and ceiling**), an ideal star
range for scoring, an activity recency window (`pushed:` qualifier), a repo-size
range, and minimum `good-first-issues`/`help-wanted-issues` counts.

The beginner ceiling — **20,000 stars** — is the number that fixes the reported bug:
it excludes `freeCodeCamp/freeCodeCamp` (~410k), `TheAlgorithms/JavaScript` (~190k),
and `microsoft/vscode` (~170k) by construction, on every path (LLM, verification, and
deterministic fallback), not just the fallback.

### 3.2 Why every prior path leaned on stars

Three independent things had to be fixed, not one:

1. `search_github_repos`'s `sort` parameter defaulted to `"stars"` with no `order`
   param sent — GitHub defaults to descending, so *any* query using the default
   returned the global top-of-star-ranking for its filters. Fixed: default is now
   `""` (relevance ranking); `sort` is only honored when explicitly one of
   `stars`/`forks`/`help-wanted-issues`/`updated`, and the deterministic path never
   passes `"stars"`.
2. The deterministic fallback's query was `stars:>50` — a floor with no ceiling,
   trivially satisfied by every repository on GitHub's front page. Fixed: replaced by
   `build_repo_query()`, which emits the tier's full band (`stars:500..20000` for
   beginner) plus a **two-pass** strategy — a strict query, and only if that returns
   nothing, a relaxed retry that widens everything **except the star ceiling**.
3. The repo agent's system prompt told Gemini "well-starred repos (100+) indicate
   community trust" as a positive signal with no ceiling, and asked for
   beginner-friendliness signals (CONTRIBUTING.md quality, maintainer
   responsiveness) the agent had no tool to check — so it could only guess. Fixed:
   the prompt now hands the agent a pre-built tier-appropriate query and instructs it
   to keep the star bound; the beginner-friendliness claims it can't verify were
   removed from the prompt entirely.

### 3.3 LLM-path verification

An LLM can still hallucinate a repository or ignore the ceiling instruction. Every
repository/issue an agent proposes is therefore re-fetched from GitHub
(`fetch_repo` / `fetch_issue_details`) before being trusted:

- A 404 (hallucinated repo) → dropped.
- Fails the tier's `reject_star_ceiling` (a looser bound than the query's own
  ceiling, since this check runs on unconstrained LLM output) → dropped.
- Survives → **rebuilt entirely from GitHub's response**, never from the model's
  self-reported fields. A fabricated star count or match score never reaches the
  frontend, because the frontend-facing object is constructed from the live fetch,
  not copied from the LLM's JSON.

If fewer than 5 repositories (or 3 issues) survive verification, the deterministic
search **tops up** the list rather than replacing it — the agent's real picks stay
ranked first, `source` on the response becomes `"hybrid"` instead of `"agent"`, and
an empty verified set alone still triggers the same deterministic fallback used for
any other agent failure.

### 3.4 Scoring

`score_repo()` / `score_issue()` (in `repo_ranking.py` / `issue_ranking.py`) replace
the old positional formula (`max(60.0, 95.0 - index*5.0)` — i.e. "95% match" meant
"first result returned," nothing about the user). Repo scoring weighs star-band fit
(log-scale position within the tier, 30%), language match (25%), topic/framework
overlap (15%, redistributed when the search item has no `topics` field — `GET
/repos/{o}/{r}` doesn't always return it, `/search/repositories` does), open-issue
supply against the tier's ideal band (15%), and push recency (15%). Issue scoring
weighs difficulty-tier fit (35%), freshness (25%), discussion health — comment count,
not just presence (20%), body quality (10%), and language match (10%). Both are pure
functions operating on raw GitHub payload dicts, so the same function scores results
from the agent path, the verification path, and the deterministic path identically.

### 3.5 Issue difficulty

The previous heuristic was a two-way label substring test that **could never return
"hard"** — `"easy" if any(term in labels for term in [...]) else "medium"`. Replaced
by `classify_issue_difficulty()`: hard-first evaluation against label patterns
(epic/RFC/architecture/security/etc.), body length, comment count, and
code-fence/checklist density, so a `good first issue`-labelled tracking epic with a
6,000-character body is no longer misreported as beginner-friendly.

## 4. Security: the token-in-prompt fix

Every agent call used to interpolate the raw GitHub OAuth token directly into the
Gemini prompt string (e.g. `f"Use the github_token '{github_token}' when calling
tools."`). The scopes requested are `read:user repo read:org` — full private-repo
write access — and this text reached Google's infrastructure (and any ADK tracing)
on every single request.

Fixed by converting each module-level `Agent` singleton (`repo_agent`, `issue_agent`,
`profile_agent`, `explainer_agent`) into a `build_*_agent(github_token)` factory. The
token is captured in a closure around each tool function; the `FunctionTool`
signature Gemini actually sees has no token parameter, so there is no way for it to
appear in the prompt or be echoed back by the model. Per-request agent construction
is pure in-process object creation — no added latency.

## 5. PostgreSQL and GitHub MCP, as wired in Phase 2

Both were deliberately left unwired through Phase 1. Phase 2 hit each trigger
condition and connected them; this section describes what is actually on the request
path today.

- **PostgreSQL** (`app/database/`): `User`, `ProfileAnalysis`, `SavedIssue` are
  defined in `models.py` and reached two ways. `api/saved.py` takes an
  `AsyncSession` through the `get_session` FastAPI dependency for the bookmark
  routes; `coordinator._persist_profile_analysis` opens `async_session` directly to
  write each profile analysis as it is produced. The trigger was the one predicted —
  saved issues needed to survive a page refresh.
- **GitHub MCP** (`app/mcp/`): the hand-rolled `mcp.ClientSession` scaffolding is
  gone, replaced by `build_github_mcp_toolset(github_token, tool_filter=...)`
  returning ADK's native `MCPToolset`, whose stdio subprocess lifecycle the ADK
  runner manages. `planner_agent.py:119` is the only caller, filtered to
  `get_file_contents` and `search_code`. The trigger was the one predicted — the
  Implementation Planner needed to read source, not just metadata.

Two properties of the MCP wiring are load-bearing and should survive any refactor.
The toolset is built **per request**, because the token lives in the subprocess
environment and a shared instance would mix one user's token into another's calls.
And the token reaches the subprocess through `GITHUB_PERSONAL_ACCESS_TOKEN` rather
than prompt text, which is the same property §4 establishes for the REST tools.

Every other GitHub call in the codebase still goes through the plain `httpx`
functions in `app/tools/github_tool.py`. MCP is additive — the planner keeps its
REST tools as a deterministic fallback for when the subprocess is unavailable.

**Partly wired: the migration runner.** One Alembic revision exists
(`b28573c7b38c_initial_schema`). Until recently it could not be applied at all:
`alembic/env.py` builds an *async* engine, but `alembic.ini` configured the sync
`postgresql://` driver, so `alembic upgrade head` died on "The asyncio extension
requires an async driver" (or, with the driver absent, `No module named 'psycopg2'`).
`env.py` now normalizes any PostgreSQL URL onto `asyncpg` and takes its default from
`app.config.settings`, so the command works against the docker-compose database.

What is still missing is anything that *invokes* it. The `lifespan` hook in
`main.py` remains an empty placeholder and no release step runs the upgrade, so
schema creation is a manual act a deployer has to remember — see §7.

## 6. Caching

`build_cache_key(namespace, *parts)` in `app/tools/utils.py` normalizes (trim,
lowercase), sorts sequence parts, and hashes when the key would otherwise be
unbounded (a caller can pass an arbitrarily long `repositories` list). All keys carry
a `CACHE_SCHEMA_VERSION` prefix (`v2` as of this phase) — bumping it on the next
ranking-shape change orphans old entries, which simply expire on their existing TTL;
no explicit flush is needed.

| Cache | Key inputs | TTL | Notes |
|---|---|---|---|
| Profile | username | 1h | |
| Repos | languages, frameworks, domains, experience_level | 30m | Previously ignored frameworks/domains — two developers with the same languages but different frameworks used to collide |
| Issues | full repository list, languages, experience_level | 15m | Previously truncated to `repositories[:3]` — two different 10-repo result sets sharing a top-3 used to collide |
| Explanation | owner/repo, issue_number | 2h | |
| Plan | owner/repo, issue_number | 2h | Added in Phase 2 alongside the Implementation Planner |

Keys stay **profile-scoped, not user-scoped**, deliberately — two beginner
Python/Django developers should share a cache entry. The original bug was
coarseness (missing dimensions) plus caching empty/failed results, not sharing
itself: every `run_*` function now skips `cache_set` when its result is empty, so a
single bad run can no longer poison every user with a matching profile for the TTL
window.

## 7. Known risks

- **Gemini free-tier 429 exhaustion.** `_run_agent` retries up to 5 times with the
  API's own suggested delay plus a buffer, defaulting to 20s. A request can stall
  ~100s before falling through to the deterministic path. Phase 1 made landing on
  that path a non-regression (same tier bands, same scoring); neither phase fixes the
  underlying rate limit — see `PRD.md` §6.
- **Nothing *invokes* the database migration.** `alembic upgrade head` now works
  (§5), but no startup hook or release step calls it. A fresh deployment still comes
  up with no schema, and every persistence route fails. This is the single largest
  gap between "works locally" and "deployable".
- **No rate limiting or request-size bounds.** `IssueDiscoveryRequest.repositories`
  has no max length; a large list multiplies GitHub calls linearly. Only
  `CommitMessageRequest` and `MentorChatRequest` carry field caps.
- **`require_github_token` costs a live GitHub round-trip on every protected
  request**, uncached. `api/saved.py` makes this worse: each of its three handlers
  calls the dependency and then repeats the same `GET /user` inline to read `login`,
  so a bookmark costs two round-trips against a rate-limited quota.
- **Mentor sessions are process-local.** `agents/mentor_session.py` holds
  conversations in a module-level dict with no eviction sweep — entries expire only
  when looked up, so abandoned sessions persist for the process lifetime. Under more
  than one worker, a follow-up question can land on a worker that has never seen the
  conversation.
- **`coordinator.py` is 1,413 lines.** Thirty-three functions covering orchestration,
  LLM-path verification, merging, and fallbacks for all seven agents. It should be
  split before Phase 3 adds PR Review and Analytics on top of it.
- **`source` on repo/issue responses (`agent` / `hybrid` / `deterministic`) is
  observability nothing consumes yet** — it exists so the fallback rate becomes
  measurable once the Analytics Agent is built.

### 7.1 Test coverage, as it stands

The Phase 1 version of this section read "no `tests/` directory, no pytest, no CI
anywhere in this repository." That is closed on the backend: **237 tests** under
`backend/tests/` (236 pass, 1 needs live credentials), and
`.github/workflows/ci.yml` runs them plus a frontend typecheck/lint/build on every
pull request. What remains:

- **The frontend has no tests and no runner.** CI proves it compiles and lints;
  nothing exercises `lib/api.ts` or the three stateful components (the dashboard's
  three-stage pipeline, the mentor chat panel, the commit generator). Their
  behavioural coverage is manual, in `MANUAL_TESTS.md`.
- **One test is deselected in CI.** Integration-marked tests need live GitHub
  credentials; run them locally with `pytest -m integration`.
- **Python 3.12 is mandatory locally, not just in CI.** `google-adk` and the async
  SQLAlchemy stack do not install on the 3.9 that macOS still puts on `PATH` as
  `python`. `README.md` §4 now says `python3.12` explicitly; a bare `python -m venv`
  produces an environment where nothing installs.
- **End-to-end verification against real GitHub OAuth and Gemini has never been
  performed.** `MANUAL_TESTS.md` is the checklist; no run of it has been recorded.

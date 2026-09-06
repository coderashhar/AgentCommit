---
name: run-agentcommit
description: Start AgentCommit locally (Postgres, Redis, FastAPI backend, Next.js frontend), verify it is actually working, and diagnose the failures this stack produces silently — a backend that looks started but never bound its port, a Docker Postgres shadowed by a native one, and Gemini quota exhaustion. Use when asked to run, start, restart, set up, or debug the local AgentCommit app, or when the dashboard hangs on "analysing".
---

# Running AgentCommit locally

Four processes: Postgres and Redis in Docker, a FastAPI backend on `:8000`, a Next.js
frontend on `:3000`. The frontend proxies `/api/proxy/*` to the backend, so a dead
backend shows up as a hang in the browser with no error anywhere.

**Verify each layer before starting the next.** Every failure this stack has produced
was silent at the layer above it.

## Start sequence

```bash
# 1. Datastores
docker compose up -d
docker ps --format '{{.Names}}\t{{.Status}}'      # both must say (healthy)

# 2. Backend  (run each line separately — see "Never paste comments" below)
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

In another shell:

```bash
# 3. Frontend
cd frontend && npm run dev
```

### Verify before opening the browser

```bash
curl -s -w '\n%{http_code}\n' localhost:8000/api/health   # must be 200
lsof -nP -iTCP:8000 -sTCP:LISTEN                          # must list a python process
```

`HTTP 000` or empty `lsof` output means the backend is **not running**, whatever the
terminal says. Go to "Backend looks started but isn't".

Check the backend's startup log for one of these lines:

- `Database schema is current (revision …)` — good.
- `Could not read the database schema version: …` — see "Postgres is shadowed".
- `Database has no Alembic revision stamped` — run `alembic upgrade head` from `backend/`.

## First-time setup

Python **3.12** is required; `google-adk` will not install on the 3.9 macOS puts on
`PATH` as `python`.

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

Environment files — there are two, and they are not interchangeable:

| File | Read by | Must contain |
|---|---|---|
| `.env` (repo root) | FastAPI backend | `GOOGLE_API_KEY`, `DATABASE_URL`, `REDIS_URL` |
| `frontend/.env.local` | Next.js / NextAuth | `AUTH_SECRET`, `AUTH_GITHUB_ID`, `AUTH_GITHUB_SECRET` |

The root `.env` may also carry the `AUTH_*` keys; the backend ignores unknown keys by
design (`extra="ignore"` in `app/config.py`). Do not remove that setting — see below.

GitHub OAuth app callback must be `http://localhost:3000/api/auth/callback/github`,
and must match whatever port the frontend actually bound.

## Known traps

### Backend looks started but isn't

`uvicorn --reload` keeps its parent process alive through an import-time exception.
The terminal shows a running process, `ps` shows it, and nothing is listening. The
frontend proxy then hangs forever and the dashboard sits on "analysing GitHub".

Reproduce the real error — `--reload` hides it:

```bash
cd backend && .venv/bin/python -c "import app.main"
```

Historically this was `pydantic ValidationError: Extra inputs are not permitted` for
`auth_github_id` / `auth_github_secret`, because `Settings` read the root `.env` while
forbidding unknown keys. Fixed by `extra="ignore"`. **That traceback also printed the
OAuth client secret in plaintext** — if you see it, rotate the secret.

### Postgres is shadowed by a native install

A native PostgreSQL binds `127.0.0.1:5432` and `[::1]:5432` *specifically*, which beats
Docker's wildcard `*:5432` for loopback connections. The container stays healthy,
`docker exec … psql` works, and every client from the host silently reaches the other
server. It surfaces as:

```
asyncpg.exceptions.InvalidAuthorizationSpecificationError: role "agentcommit" does not exist
```

Diagnose:

```bash
lsof -nP -iTCP:5432 -sTCP:LISTEN     # two owners = shadowed
```

Fix without disturbing other projects on the native server:

```bash
echo 'POSTGRES_PORT=5433' >> .env
# change the port in DATABASE_URL to 5433 as well
docker compose up -d --force-recreate postgres
cd backend && alembic upgrade head
```

Only persistence (saved issues, profile history) breaks while this is unfixed. The
agent routes keep working.

### Port 3000 taken by another project

Next.js silently increments to `:3001`. NextAuth then mismatches `AUTH_URL` and the
registered OAuth callback, and sign-in fails. Check what actually bound:

```bash
lsof -nP -iTCP -sTCP:LISTEN | grep node
```

Either free `:3000`, or set `AUTH_URL` to the real port **and** add the matching
callback URL to the GitHub OAuth app.

### Gemini quota exhaustion

Free tier is **20 requests/minute** for `gemini-2.5-flash`. One dashboard load runs
three agents in sequence, and each agent makes several calls through its tool loop, so
a single page view can exhaust it.

Check directly:

```bash
KEY=$(grep '^GOOGLE_API_KEY=' .env | cut -d= -f2-)
curl -s -X POST -H 'Content-Type: application/json' \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$KEY" \
  -d '{"contents":[{"parts":[{"text":"ok"}]}]}' | head -c 400
```

A `429 RESOURCE_EXHAUSTED` means the LLM path is unavailable. `_run_agent` has a 30s
total retry budget (`AGENT_RETRY_BUDGET_SECONDS`), so requests now fail fast to the
deterministic fallback in ~1s instead of stalling minutes. Responses carry
`source: "deterministic"` rather than `"agent"` — the app still works, results are just
tier-ranked GitHub search rather than model output. Wait for the window to reset or
move to a paid key.

**Do not raise the retry budget to "fix" this.** Gemini's suggested delay scales with
exhaustion — it asked for 57.7s once. Sleeping that five times per agent, three agents
deep, is how one page load took 15 minutes.

### Never paste commands with trailing `#` comments

zsh does not treat `#` as a comment interactively unless `interactive_comments` is set.
Pasting `python3.12 -m venv .venv  # must be 3.12` makes venv create a directory for
every word after the `#`. Keep comments on their own lines in anything meant to be
copied.

## Verification checklist

Run the suite first — it catches a broken environment faster than the UI:

```bash
cd backend && pytest -m "not integration"    # what CI runs
```

Then, in the browser:

1. **Sign in with GitHub** → lands on `/dashboard`.
2. **Dashboard pipeline** → profile → repos → issues populate in sequence. Should take
   seconds. Minutes means quota exhaustion plus a stale retry budget.
3. **Bookmark an issue** → refresh → still bookmarked. This is the only Postgres path;
   it fails while Postgres is shadowed.
4. **Open an issue** → explanation renders → "Generate Implementation Plan" works.
5. **Mentor chat** → ask a question, then a follow-up referring to the first answer.
   Context must carry across turns.
6. **Commit generator** → with and without a pasted diff; subject ≤72 chars.
7. **Kill the backend mid-session** → UI shows an error with a retry button, not a
   blank screen.

`MANUAL_TESTS.md` at the repo root is the exhaustive version.

## Useful state dump

When something is wrong and the cause is not obvious:

```bash
curl -s -o /dev/null -w 'backend:%{http_code}\n' localhost:8000/api/health
curl -s -o /dev/null -w 'frontend:%{http_code}\n' localhost:3000
lsof -nP -iTCP -sTCP:LISTEN | grep -E 'node|python|docker'
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
git log --oneline -1
```

A stale local `main` has caused this before: a merged PR plus an un-pulled local branch
reverts the working tree to broken code. Check `git log --oneline -1` against the remote
before debugging anything else.

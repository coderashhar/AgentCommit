# AgentCommit — Product Requirements Document

**Status:** Living document, updated alongside `PROJECT_HISTORY.md`.
**Companion doc:** `ARCHITECTURE.md` covers the technical design behind this scope.

---

## 1. Problem statement

AgentCommit exists to solve the "first contribution cliff": a developer wants to
contribute to open source, doesn't know where to start, and the honest options are
either (a) browse `github.com/topics/good-first-issue` and get lost in a wall of
projects with no sense of fit, or (b) ask an LLM directly and get generic, unranked
suggestions with no connection to the developer's actual GitHub history.

**The MVP built to solve this shipped with the opposite failure mode.** The dashboard
recommended `microsoft/vscode`, `freeCodeCamp/freeCodeCamp`, and `TheAlgorithms/*` —
the most popular repositories on GitHub, regardless of language, and regardless of
whether a first-time contributor could plausibly get a PR merged there. Root cause
(see `ARCHITECTURE.md` for the full trace): every ranking path — the LLM's system
prompt, its search-tool default, and the deterministic fallback — used **stars as the
primary or sole ranking signal**, with only a floor and no ceiling. A repository with
170,000 stars and an hours-long build has a PR queue measured in weeks and a
maintainer team with no bandwidth to onboard a newcomer; it is a worse target for a
first contribution than a 3,000-star project with four open `good first issue` labels
and a maintainer who responds within days.

This is the motivating case study for the tiered-recommendation redesign this PRD's
Phase 1 scope covers.

---

## 2. Target users

Carried forward from `ROADMAP.md`, refined with the "cliff" framing:

- **First-time contributors** — never opened a PR against someone else's repo. Need:
  small, active, well-labelled projects; issues explained in plain English; explicit
  permission to try.
- **Hacktoberfest / GSSoC participants** — time-boxed, motivated by a specific event,
  often supplementing a checklist with real understanding. Need: fast triage across
  many candidate issues, difficulty signal they can trust.
- **Students building a portfolio** — want contributions that read well on a resume.
  Need: recognizable-but-tractable repositories, a record of what they did and why.
- **Developers re-entering open source after a gap, or switching stacks** — have
  general engineering experience but no track record in this specific
  language/ecosystem yet. Need: intermediate-tier repos that don't waste their time
  but also don't assume deep codebase familiarity.
- **Experienced developers looking for relevant projects** — the advanced tier. Need:
  the ceiling relaxed, `help-wanted-issues` as the real approachability signal instead
  of `good-first-issues`.

## 3. Jobs to be done

1. "Tell me which repositories, out of millions on GitHub, are actually plausible for
   *me* — my languages, my experience level — to contribute to."
2. "Tell me which open issue in a repository I've already vetted is worth my next few
   hours, and how hard it actually is."
3. "Explain the issue like a mentor would, not like a ticket — what's actually being
   asked, what do I need to know, where do I start."
4. (Phase 2+) "Help me plan the change, review my code before I open a PR, and write
   the commit message."

This PRD's Phase 1 scope covers job 1 and 2 completely, and job 3 partially (the
explainer agent exists but its difficulty rating inherited the same too-generous
label-substring heuristic the repo/issue ranking had, and is fixed alongside it).

## 4. Scope by phase

### Phase 1 (this document's active scope) — Stabilization + tiered recommendations
- Repository recommendations tiered by experience level (beginner / intermediate /
  advanced), each with its own star ceiling, activity window, size band, and
  labelled-issue threshold — see `ARCHITECTURE.md` for the exact bands.
- Issue recommendations spread across all candidate repositories (not just the
  top 5), filtered to unassigned, open, non-stale, non-PR issues, with a real
  three-way difficulty classifier that can return "hard."
- LLM-path verification: every repository and issue an agent proposes is re-fetched
  from GitHub and rebuilt from ground truth before being shown, so a hallucinated or
  over-broad LLM suggestion can never reach the user unchecked.
- P0 correctness fixes: the issue-detail page (previously non-functional for every
  click), route protection, and retryable error states.
- Security: the user's GitHub OAuth token no longer appears in Gemini prompt text.

### Phase 2 — Planning, mentoring, commit generation
- Implementation Planner Agent, Mentor Agent, Commit Message Agent (per `ROADMAP.md`).
- Real persistence: `ProfileAnalysis` and `SavedIssue` tables are wired up (they exist
  in the schema today but nothing reads or writes them — see `ARCHITECTURE.md`'s
  deferred-scaffolding section). Triggered by the first feature that needs history:
  "issues I've saved," "repos I've looked at before."
- GitHub MCP wired into agents that need repo file browsing (e.g. the Planner Agent
  reading source files to propose a diff) — currently scaffolded but unused.
- A real test suite. There is none today; this is the single largest reason Phase 1
  shipped a regression as visible as the mega-repo problem without anyone catching it
  in CI.

### Phase 3 — PR Review, analytics, contribution tracking
Per `ROADMAP.md`: PR Review Agent, repository insights, contribution analytics.

### Phase 4 — Ecosystem integrations
Per `ROADMAP.md`: Discord/Slack bots, VS Code extension, browser extension.

## 5. Success metrics

The metric that mattered for this PRD's Phase 1 work and was previously
unmeasurable: **share of recommended repositories a target-tier user could plausibly
land a first PR in.** There was no instrumentation for this before Phase 1; the
`RecommendedRepo.tier` and `.verified` fields added in this phase (see
`ARCHITECTURE.md`) are the groundwork for tracking it going forward.

Other metrics, roughly in the order they become measurable:
- **Recommendation quality (proxy, available today):** for beginner-tier users, 0%
  of recommended repositories should exceed the tier's star ceiling (20,000). This is
  a hard invariant, not a target — see the regression check in `ARCHITECTURE.md`.
- **Pipeline completion rate:** % of dashboard loads that reach `agentStep === "done"`
  without hitting the error state. Not yet instrumented; requires basic analytics
  (out of scope for Phase 1).
- **Time-to-first-issue-click:** how quickly a user goes from landing on `/dashboard`
  to opening an issue detail page. Proxy for "did the recommendations feel relevant
  enough to act on."
- **Fallback rate:** `RepoRecommendationResponse.source` (`agent` / `hybrid` /
  `deterministic`) is now returned on every response specifically so this is
  observable — how often the LLM path degrades to the deterministic path, which was
  previously invisible (see "Known risks" in `ARCHITECTURE.md`).
- **Longer-term, product-level:** contributions actually made (PRs opened, merged)
  by users who went through AgentCommit — the north star, requires Phase 3's
  analytics.

## 6. Non-goals (Phase 1)

- **Not building persistence.** `ProfileAnalysis`/`SavedIssue` tables stay unwired.
  Nothing in Phase 1's scope needs a user's history to survive a page refresh.
- **Not wiring GitHub MCP.** No agent in Phase 1's scope needs to browse repository
  files; the existing `httpx`-based GitHub REST calls are sufficient.
- **Not building a test suite or CI.** Acknowledged as a real gap (see Phase 2 and
  `ARCHITECTURE.md`'s known risks) but out of scope for this pass — the new ranking
  modules are written pure specifically so this debt is cheap to pay down later.
- **Not rate-limiting the API.** No abuse-prevention layer exists; deferred until
  there's real traffic to protect against.
- **Not solving the free-tier Gemini 429 problem.** Retried with backoff, but a
  request can still stall on 5 retries before falling through to the deterministic
  path. Making the deterministic path *good* (this phase's core work) is the
  mitigation; removing the underlying rate limit is a cost/infra decision, not a
  product one.

"""Coordinator — runs each sub-agent per request and falls back to deterministic
GitHub-only recommendations when the agent path is unavailable.

There is no live multi-agent orchestration here despite the module name: each
`run_*` function builds and runs exactly one ADK agent, bound to the current
request's GitHub token, then either trusts its (verified) output or falls back to a
tiered deterministic search. Recommendations — both the agent's and the fallback's —
are ranked using `app.tools.repo_ranking` / `app.tools.issue_ranking`, which encode
experience-tier bands (star ceilings, activity windows, issue-supply targets) so a
beginner never sees mega-repos like microsoft/vscode regardless of which path served
the response.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agents.explainer_agent import build_explainer_agent
from app.agents.issue_agent import build_issue_agent
from app.agents.profile_agent import build_profile_agent
from app.agents.repo_agent import build_repo_agent
from app.models.schemas import (
    ProfileAnalysisResponse,
    RepoRecommendationResponse,
    RecommendedRepo,
    IssueDiscoveryResponse,
    DiscoveredIssue,
    IssueExplanationResponse,
)
from app.tools.github_tool import (
    fetch_github_profile,
    fetch_issue_details,
    fetch_repo,
    fetch_repo_readme,
    fetch_user_repos,
    search_github_issues,
    search_github_repos,
)
from app.tools.issue_ranking import (
    IssueScore,
    is_claimed,
    is_pull_request,
    is_stale_issue,
    score_issue,
)
from app.tools.repo_ranking import (
    ExperienceTier,
    RepoScore,
    build_repo_query,
    format_match_reason,
    repo_is_rejected,
    score_repo,
)
from app.tools.utils import build_cache_key, cache_get, cache_set, truncate_text

logger = logging.getLogger(__name__)

# Session service for managing agent conversations
session_service = InMemorySessionService()

FRAMEWORK_KEYWORDS = {
    "react": "React",
    "next": "Next.js",
    "nextjs": "Next.js",
    "vue": "Vue",
    "angular": "Angular",
    "svelte": "Svelte",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "express": "Express",
    "node": "Node.js",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "tailwind": "Tailwind CSS",
    "spring": "Spring",
    "laravel": "Laravel",
}

DOMAIN_KEYWORDS = {
    "web": "web development",
    "frontend": "web development",
    "backend": "backend development",
    "api": "backend development",
    "machine-learning": "machine learning",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "devops": "devops",
    "cli": "developer tooling",
    "mobile": "mobile development",
    "ios": "mobile development",
    "android": "mobile development",
    "data": "data engineering",
}

# Verification / deterministic-search tuning.
VERIFY_CONCURRENCY = 5
MIN_REPO_RESULTS = 5
MAX_REPO_RESULTS = 10
MAX_CANDIDATE_REPOS = MAX_REPO_RESULTS * 2
MAX_ISSUES_PER_REPO = 2
ISSUE_SOURCE_REPO_LIMIT = 12
MAX_ISSUE_RESULTS = 10
ISSUE_SEARCH_LABELS = ("good first issue", "help wanted", "documentation")


def _extract_retry_delay(error_msg: str) -> float:
    """Extract the retry delay from a Gemini 429 error message."""
    match = re.search(r'retry in (\d+(?:\.\d+)?)s', str(error_msg), re.IGNORECASE)
    if match:
        return float(match.group(1))
    match = re.search(r"retryDelay.*?(\d+)s", str(error_msg), re.IGNORECASE)
    if match:
        return float(match.group(1))
    return 20.0  # safe default


def _event_text(event: object) -> str:
    """Collect all text parts from an ADK event."""
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) or []
    text_parts: list[str] = []

    for part in parts:
        text = getattr(part, "text", None)
        if text:
            text_parts.append(text)

    return "\n".join(text_parts).strip()


async def _run_agent(
    agent: Agent,
    user_message: str,
    session_id: str,
    max_retries: int = 5,
) -> str:
    """Run an ADK agent with a user message and return the text response.

    Automatically retries on 429 RESOURCE_EXHAUSTED errors with the delay
    specified by the Gemini API, plus a small buffer.

    Args:
        agent: The ADK agent to run.
        user_message: The message/instruction to send.
        session_id: Unique session identifier.
        max_retries: Maximum number of retries on rate limit errors.

    Returns:
        The agent's text response.
    """
    for attempt in range(max_retries + 1):
        try:
            runner = Runner(
                agent=agent,
                app_name="agentcommit",
                session_service=session_service,
            )

            session = await session_service.create_session(
                app_name="agentcommit",
                user_id="system",
            )

            user_content = types.Content(
                role="user",
                parts=[types.Part(text=user_message)],
            )

            final_response = ""
            async for event in runner.run_async(
                session_id=session.id,
                user_id="system",
                new_message=user_content,
            ):
                event_text = _event_text(event)
                if event_text:
                    final_response = event_text

                if event.is_final_response() and event_text:
                    final_response = event_text

            return final_response

        except Exception as e:
            error_str = str(e)
            is_rate_limit = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str

            if is_rate_limit and attempt < max_retries:
                delay = _extract_retry_delay(error_str) + 2.0  # add buffer
                logger.warning(
                    "Rate limited (attempt %d/%d). Waiting %.1fs before retry...",
                    attempt + 1, max_retries, delay,
                )
                await asyncio.sleep(delay)
                continue

            # Not a rate limit error, or we've exhausted retries
            raise


def _parse_json_response(response: str) -> dict:
    """Extract and parse JSON from an agent's response text.

    The agent may wrap JSON in markdown code blocks.
    """
    text = response.strip()
    if not text:
        raise RuntimeError("Agent returned an empty response")

    # Robustly extract JSON object by finding the first '{' and last '}'
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end+1]

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse agent response as JSON. Raw response:\n{text}")
        raise RuntimeError(f"Agent did not return valid JSON: {str(e)}")


def _ordered_unique(values: list[str]) -> list[str]:
    """Return unique strings while preserving first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        result.append(normalized)
    return result


def _infer_keywords(repos: list[dict], keyword_map: dict[str, str]) -> list[str]:
    """Infer normalized tags from repository names, descriptions, and topics."""
    matches: list[str] = []
    for repo in repos:
        haystack = " ".join(
            [
                str(repo.get("name") or ""),
                str(repo.get("description") or ""),
                " ".join(repo.get("topics") or []),
            ]
        ).lower()
        for keyword, label in keyword_map.items():
            if keyword in haystack:
                matches.append(label)
    return _ordered_unique(matches)


def _repo_language(repo: dict) -> str | None:
    language = repo.get("language")
    return language if isinstance(language, str) and language else None


def _repo_full_name(repo: dict) -> str | None:
    full_name = repo.get("full_name")
    return full_name if isinstance(full_name, str) and full_name else None


def _fallback_experience_level(repos: list[dict]) -> str:
    repo_count = len(repos)
    total_stars = sum(int(repo.get("stargazers_count") or 0) for repo in repos)
    has_many_languages = len({_repo_language(repo) for repo in repos if _repo_language(repo)}) >= 4

    if repo_count >= 20 or total_stars >= 100 or has_many_languages:
        return "advanced"
    if repo_count >= 6 or total_stars >= 20:
        return "intermediate"
    return "beginner"


def _repo_from_github(
    repo: dict,
    tier: ExperienceTier,
    repo_score: RepoScore,
    match_reason: str = "",
    verified: bool = False,
) -> RecommendedRepo | None:
    """Build a RecommendedRepo entirely from GitHub's fields plus a computed score.

    Every displayed field comes from `repo` (GitHub's response), never from a model's
    self-reported values — this is what makes hallucinated repos harmless even if one
    slips past verification and what keeps fallback results honest.
    """
    full_name = _repo_full_name(repo)
    if not full_name:
        return None

    return RecommendedRepo(
        full_name=full_name,
        description=repo.get("description") or "",
        stars=int(repo.get("stargazers_count") or repo.get("stars") or 0),
        language=repo.get("language") or "",
        topics=repo.get("topics") or [],
        open_issues_count=int(repo.get("open_issues_count") or 0),
        html_url=repo.get("html_url") or "",
        match_score=repo_score.score,
        match_reason=match_reason or format_match_reason(repo_score.reasons, tier),
        forks=int(repo.get("forks_count") or repo.get("forks") or 0),
        pushed_at=repo.get("pushed_at") or "",
        tier=tier.value,
        verified=verified,
    )


def _issue_from_github(
    issue: dict,
    repo_full_name: str,
    issue_score: IssueScore,
    verified: bool = False,
) -> DiscoveredIssue | None:
    """Build a DiscoveredIssue entirely from GitHub's fields plus a computed score."""
    title = issue.get("title")
    number = issue.get("number")
    if not isinstance(title, str) or not isinstance(number, int):
        return None

    labels = [
        label.get("name", "")
        for label in issue.get("labels") or []
        if isinstance(label, dict) and label.get("name")
    ]
    body = issue.get("body") or ""

    return DiscoveredIssue(
        title=title,
        number=number,
        repo_full_name=repo_full_name,
        labels=labels,
        html_url=issue.get("html_url") or "",
        created_at=issue.get("created_at") or "",
        comments=int(issue.get("comments") or 0),
        body_preview=truncate_text(body, 200) if body else "",
        difficulty=issue_score.difficulty,
        match_score=issue_score.score,
        updated_at=issue.get("updated_at") or "",
        verified=verified,
    )


async def _fallback_profile_analysis(username: str, github_token: str) -> ProfileAnalysisResponse:
    """Build a profile analysis directly from GitHub data when the agent is unavailable."""
    profile = await fetch_github_profile(username, github_token)
    repos = await fetch_user_repos(username, github_token, per_page=50)

    if profile.get("error"):
        raise RuntimeError(profile["error"])
    if repos and repos[0].get("error"):
        raise RuntimeError(repos[0]["error"])

    languages = _ordered_unique(
        [language for repo in repos if (language := _repo_language(repo))]
    )
    frameworks = _infer_keywords(repos, FRAMEWORK_KEYWORDS)
    domains = _infer_keywords(repos, DOMAIN_KEYWORDS)
    top_repositories = [
        full_name
        for repo in sorted(
            repos,
            key=lambda item: int(item.get("stargazers_count") or 0),
            reverse=True,
        )[:5]
        if (full_name := _repo_full_name(repo))
    ]
    experience_level = _fallback_experience_level(repos)

    display_name = profile.get("name") or username
    primary_languages = ", ".join(languages[:3]) if languages else "public repositories"
    summary = (
        f"{display_name} works primarily with {primary_languages}. "
        f"Based on {len(repos)} public repositories, AgentCommit estimates a "
        f"{experience_level} open source experience level."
    )

    return ProfileAnalysisResponse(
        username=profile.get("login") or username,
        languages=languages[:10],
        frameworks=frameworks[:10],
        experience_level=experience_level,
        domains=domains[:8],
        top_repositories=top_repositories,
        summary=summary,
    )


async def _search_tier_repos(
    tier: ExperienceTier,
    languages: list[str],
    frameworks: list[str],
    domains: list[str],
    github_token: str,
) -> list[dict]:
    """Search GitHub for repositories inside a tier's bands, strict then relaxed.

    Ranks by help-wanted-issues first (a direct "wants outside contributors" signal),
    then by relevance. Never sorts by stars — see `search_github_repos`.
    """
    search_terms = languages[:3] or frameworks[:3] or domains[:2] or ["javascript"]
    candidates: dict[str, dict] = {}

    for term in search_terms:
        for relaxed in (False, True):
            if len(candidates) >= MAX_CANDIDATE_REPOS:
                break
            query = build_repo_query(tier, language=term, relaxed=relaxed)
            for sort in ("help-wanted-issues", ""):
                repos = await search_github_repos(query, github_token, sort=sort, per_page=25)
                found_any = False
                for repo in repos:
                    if repo.get("error"):
                        continue
                    full_name = _repo_full_name(repo)
                    if not full_name or full_name in candidates:
                        continue
                    candidates[full_name] = repo
                    found_any = True
                    if len(candidates) >= MAX_CANDIDATE_REPOS:
                        break
                if len(candidates) >= MAX_CANDIDATE_REPOS:
                    break
            # A strict pass that returned nothing at all means the relaxed retry is
            # worth trying; a strict pass with any hits is trusted as-is.
            if not relaxed and candidates:
                break

    return list(candidates.values())


async def _deterministic_repo_recommendation(
    languages: list[str],
    frameworks: list[str],
    domains: list[str],
    experience_level: str,
    github_token: str,
) -> RepoRecommendationResponse:
    """Recommend repositories from tiered GitHub search when the agent is unavailable."""
    tier = ExperienceTier.from_experience_level(experience_level)
    raw_repos = await _search_tier_repos(tier, languages, frameworks, domains, github_token)

    scored: list[tuple[RepoScore, dict]] = []
    for repo in raw_repos:
        if repo_is_rejected(repo, tier):
            continue
        scored.append((score_repo(repo, tier, languages, frameworks, domains), repo))

    scored.sort(key=lambda pair: pair[0].score, reverse=True)

    recommended: list[RecommendedRepo] = []
    for repo_score, repo in scored[:MAX_REPO_RESULTS]:
        built = _repo_from_github(repo, tier, repo_score, verified=True)
        if built:
            recommended.append(built)

    return RepoRecommendationResponse(repositories=recommended, source="deterministic")


async def _search_tier_issues(
    repositories: list[str],
    tier: ExperienceTier,
    languages: list[str],
    github_token: str,
) -> list[tuple[dict, str]]:
    """Search unassigned, open, non-PR issues across repositories, label-major.

    The (label, repo) searches are independent of each other, so they run
    concurrently behind a semaphore rather than sequentially — up to
    len(ISSUE_SEARCH_LABELS) * ISSUE_SOURCE_REPO_LIMIT calls otherwise, awaited one
    at a time. Results are then processed in label-major order (labels outer, repos
    inner) with a per-repo cap, so one prolific repository still can't consume the
    entire result set — the opposite of the repo-major, early-return loop this
    replaces — the cap just applies to which results are *kept* rather than which
    searches are *issued*.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")
    target_repos = repositories[:ISSUE_SOURCE_REPO_LIMIT]
    semaphore = asyncio.Semaphore(VERIFY_CONCURRENCY)

    async def fetch_bounded(labels: str, repo_full_name: str) -> tuple[str, str, list[dict]]:
        async with semaphore:
            issues = await search_github_issues(
                repo_full_name=repo_full_name,
                github_token=github_token,
                labels=labels,
                assignee="none",
                since=since,
                per_page=5,
            )
        return labels, repo_full_name, issues

    results = await asyncio.gather(
        *(
            fetch_bounded(labels, repo_full_name)
            for labels in ISSUE_SEARCH_LABELS
            for repo_full_name in target_repos
        ),
        return_exceptions=True,
    )

    # Index by (labels, repo) so results can be replayed in the same label-major
    # order the searches were declared in, keeping the per-repo cap deterministic
    # regardless of which concurrent request happens to finish first.
    by_label_and_repo: dict[tuple[str, str], list[dict]] = {}
    for outcome in results:
        if isinstance(outcome, BaseException):
            continue
        labels, repo_full_name, issues = outcome
        by_label_and_repo[(labels, repo_full_name)] = issues

    collected: dict[str, tuple[dict, str]] = {}
    per_repo_counts: dict[str, int] = {}

    for labels in ISSUE_SEARCH_LABELS:
        for repo_full_name in target_repos:
            if per_repo_counts.get(repo_full_name, 0) >= MAX_ISSUES_PER_REPO:
                continue

            for issue in by_label_and_repo.get((labels, repo_full_name), []):
                if issue.get("error") or is_pull_request(issue) or is_claimed(issue):
                    continue
                if is_stale_issue(issue):
                    continue
                number = issue.get("number")
                if number is None:
                    continue
                issue_key = f"{repo_full_name}#{number}"
                if issue_key in collected:
                    continue
                if per_repo_counts.get(repo_full_name, 0) >= MAX_ISSUES_PER_REPO:
                    continue

                collected[issue_key] = (issue, repo_full_name)
                per_repo_counts[repo_full_name] = per_repo_counts.get(repo_full_name, 0) + 1

    return list(collected.values())


async def _deterministic_issue_discovery(
    repositories: list[str],
    languages: list[str],
    experience_level: str,
    github_token: str,
) -> IssueDiscoveryResponse:
    """Discover issues directly from GitHub labels when the agent is unavailable."""
    tier = ExperienceTier.from_experience_level(experience_level)
    raw_issues = await _search_tier_issues(repositories, tier, languages, github_token)
    repo_languages = await _fetch_repo_languages(repositories, github_token)

    scored: list[tuple[IssueScore, dict, str]] = []
    for issue, repo_full_name in raw_issues:
        issue_score = score_issue(
            issue, tier, languages, repo_language=repo_languages.get(repo_full_name, "")
        )
        scored.append((issue_score, issue, repo_full_name))

    scored.sort(key=lambda triple: triple[0].score, reverse=True)

    discovered: list[DiscoveredIssue] = []
    for issue_score, issue, repo_full_name in scored[:MAX_ISSUE_RESULTS]:
        built = _issue_from_github(issue, repo_full_name, issue_score, verified=True)
        if built:
            discovered.append(built)

    return IssueDiscoveryResponse(issues=discovered, source="deterministic")


async def _fallback_issue_explanation(
    owner: str,
    repo: str,
    issue_number: int,
    github_token: str,
) -> IssueExplanationResponse:
    """Create a basic issue explanation from GitHub issue details."""
    issue = await fetch_issue_details(owner, repo, issue_number, github_token)
    if issue.get("error"):
        raise RuntimeError(issue["error"])

    readme = await fetch_repo_readme(owner, repo, github_token)
    labels = [
        label.get("name", "")
        for label in issue.get("labels") or []
        if isinstance(label, dict) and label.get("name")
    ]
    body = issue.get("body") or "The issue body is empty, so start by reading the discussion on GitHub."
    comments = int(issue.get("comments") or 0)
    difficulty_label = score_issue(issue, ExperienceTier.BEGINNER, []).difficulty
    difficulty = {"easy": 1, "medium": 3, "hard": 5}[difficulty_label]
    concepts = _ordered_unique(labels + ["GitHub issues", f"{owner}/{repo} project context"])[:6]
    readme_hint = " Review the project README for setup and contribution context." if readme else ""

    return IssueExplanationResponse(
        title=issue.get("title") or f"{owner}/{repo} issue #{issue_number}",
        summary=truncate_text(body, 700),
        difficulty=difficulty,
        estimated_time="1-3 hours" if difficulty <= 2 else ("3-6 hours" if difficulty <= 3 else "6+ hours"),
        required_concepts=concepts,
        learning_resources=[
            f"https://github.com/{owner}/{repo}",
            f"https://github.com/{owner}/{repo}/issues/{issue_number}",
        ],
        suggested_approach=(
            "Read the full issue and linked discussion, reproduce the problem locally, "
            "identify the smallest relevant files, make a focused change, then run the "
            f"project tests or checks before opening a pull request.{readme_hint}"
        ),
        files_to_explore=["README.md", "CONTRIBUTING.md", "tests/"],
    )


async def _fetch_repo_for_verification(full_name: str, github_token: str) -> tuple[str, dict]:
    owner, _, name = full_name.partition("/")
    result = await fetch_repo(owner, name, github_token)
    return full_name, result


async def _fetch_repo_languages(repo_full_names: list[str], github_token: str) -> dict[str, str]:
    """Look up each repository's primary language for issue-side language scoring.

    GitHub's single-issue endpoint (`fetch_issue_details`) never includes a nested
    repository object, so `score_issue`'s language-match signal would otherwise
    always fall back to its neutral default. Bounded by the (already-capped)
    candidate repo count, so this stays a handful of calls, not one per issue.
    """
    unique_names = list(dict.fromkeys(repo_full_names))
    semaphore = asyncio.Semaphore(VERIFY_CONCURRENCY)

    async def fetch_bounded(full_name: str) -> tuple[str, dict]:
        async with semaphore:
            return await _fetch_repo_for_verification(full_name, github_token)

    results = await asyncio.gather(
        *(fetch_bounded(name) for name in unique_names),
        return_exceptions=True,
    )

    languages: dict[str, str] = {}
    for outcome in results:
        if isinstance(outcome, BaseException):
            continue
        full_name, repo_data = outcome
        if repo_data.get("error"):
            continue
        language = repo_data.get("language")
        if isinstance(language, str) and language:
            languages[full_name] = language
    return languages


async def _verify_recommended_repos(
    repos: list[RecommendedRepo],
    tier: ExperienceTier,
    languages: list[str],
    frameworks: list[str],
    domains: list[str],
    github_token: str,
) -> list[RecommendedRepo]:
    """Re-fetch each LLM-proposed repo from GitHub and rebuild it from ground truth.

    A hallucinated repo returns a 404 here and is dropped; a real repo is rebuilt
    entirely from GitHub's response, so a fabricated star count never reaches the
    frontend. The LLM's `match_reason` is kept when it looks genuine (that's the one
    field where the model can add value); its `match_score` is always recomputed.
    """
    candidates: list[str] = []
    seen: set[str] = set()
    for repo in repos:
        full_name = repo.full_name.strip()
        owner, sep, name = full_name.partition("/")
        if not sep or not owner or not name:
            continue
        key = full_name.lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(full_name)
        if len(candidates) >= MAX_CANDIDATE_REPOS:
            break

    original_reasons = {repo.full_name.lower(): repo.match_reason for repo in repos}

    semaphore = asyncio.Semaphore(VERIFY_CONCURRENCY)

    async def fetch_bounded(full_name: str) -> tuple[str, dict]:
        async with semaphore:
            return await _fetch_repo_for_verification(full_name, github_token)

    results = await asyncio.gather(
        *(fetch_bounded(full_name) for full_name in candidates),
        return_exceptions=True,
    )

    verified: list[tuple[RepoScore, RecommendedRepo]] = []
    for outcome in results:
        if isinstance(outcome, BaseException):
            continue
        full_name, repo_data = outcome
        if repo_data.get("error"):
            continue
        if repo_is_rejected(repo_data, tier):
            continue

        repo_score = score_repo(repo_data, tier, languages, frameworks, domains)
        llm_reason = original_reasons.get(full_name.lower(), "")
        reason = llm_reason if llm_reason and len(llm_reason) <= 400 else ""
        built = _repo_from_github(repo_data, tier, repo_score, match_reason=reason, verified=True)
        if built:
            verified.append((repo_score, built))

    verified.sort(key=lambda pair: pair[0].score, reverse=True)
    return [repo for _, repo in verified[:MAX_REPO_RESULTS]]


async def _verify_discovered_issues(
    issues: list[DiscoveredIssue],
    tier: ExperienceTier,
    languages: list[str],
    github_token: str,
) -> list[DiscoveredIssue]:
    """Re-fetch each LLM-proposed issue and drop anything that fails validation.

    The LLM path has no built-in filter for pull requests or claimed issues — only
    the deterministic path applies those via query parameters — so this is the only
    place that filters them out of agent-sourced results.
    """
    seen: set[str] = set()
    candidates: list[DiscoveredIssue] = []
    for issue in issues:
        key = f"{issue.repo_full_name.lower()}#{issue.number}"
        if key in seen:
            continue
        seen.add(key)
        candidates.append(issue)

    semaphore = asyncio.Semaphore(VERIFY_CONCURRENCY)

    async def fetch_bounded(issue: DiscoveredIssue) -> tuple[DiscoveredIssue, dict]:
        owner, _, repo = issue.repo_full_name.partition("/")
        async with semaphore:
            data = await fetch_issue_details(owner, repo, issue.number, github_token)
        return issue, data

    results, repo_languages = await asyncio.gather(
        asyncio.gather(*(fetch_bounded(issue) for issue in candidates), return_exceptions=True),
        _fetch_repo_languages([issue.repo_full_name for issue in candidates], github_token),
    )

    verified: list[tuple[IssueScore, DiscoveredIssue]] = []
    per_repo_counts: dict[str, int] = {}
    for outcome in results:
        if isinstance(outcome, BaseException):
            continue
        original, issue_data = outcome
        if issue_data.get("error"):
            continue
        if is_pull_request(issue_data) or is_claimed(issue_data):
            continue
        if issue_data.get("state") != "open" or issue_data.get("locked"):
            continue
        if is_stale_issue(issue_data):
            continue
        if per_repo_counts.get(original.repo_full_name, 0) >= MAX_ISSUES_PER_REPO:
            continue

        repo_language = repo_languages.get(original.repo_full_name, "")
        issue_score = score_issue(issue_data, tier, languages, repo_language=repo_language)
        built = _issue_from_github(issue_data, original.repo_full_name, issue_score, verified=True)
        if built:
            verified.append((issue_score, built))
            per_repo_counts[original.repo_full_name] = per_repo_counts.get(original.repo_full_name, 0) + 1

    verified.sort(key=lambda pair: pair[0].score, reverse=True)
    return [issue for _, issue in verified[:MAX_ISSUE_RESULTS]]


def _merge_repos_by_full_name(
    primary: list[RecommendedRepo], supplement: list[RecommendedRepo]
) -> list[RecommendedRepo]:
    """Top up `primary` with items from `supplement` not already present."""
    seen = {repo.full_name.lower() for repo in primary}
    merged = list(primary)
    for repo in supplement:
        key = repo.full_name.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(repo)
    return merged


def _merge_issues_by_key(
    primary: list[DiscoveredIssue], supplement: list[DiscoveredIssue]
) -> list[DiscoveredIssue]:
    """Top up `primary` with items from `supplement` not already present."""
    seen = {f"{issue.repo_full_name.lower()}#{issue.number}" for issue in primary}
    merged = list(primary)
    for issue in supplement:
        key = f"{issue.repo_full_name.lower()}#{issue.number}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(issue)
    return merged


async def run_profile_analysis(
    username: str,
    github_token: str,
) -> ProfileAnalysisResponse:
    """Run the Profile Analyzer Agent for a given GitHub user.

    Results are cached in Redis for 1 hour.
    """
    cache_key = build_cache_key("profile", username)
    cached = await cache_get(cache_key)
    if cached:
        logger.info("Returning cached profile analysis for %s", username)
        return ProfileAnalysisResponse(**cached)

    message = (
        f"Analyze the GitHub profile for user '{username}'. "
        f"Return the analysis as a structured JSON object."
    )

    try:
        agent = build_profile_agent(github_token)
        response = await _run_agent(agent, message, f"profile-{username}")
        data = _parse_json_response(response)
        result = ProfileAnalysisResponse(**data)
    except Exception as e:
        logger.warning("Profile agent failed (%s); using GitHub fallback: %s", type(e).__name__, str(e))
        result = await _fallback_profile_analysis(username, github_token)

    if result.username:
        await cache_set(cache_key, result.model_dump(), ttl_seconds=3600)

    return result


async def run_repo_recommendation(
    languages: list[str],
    frameworks: list[str],
    experience_level: str,
    domains: list[str],
    github_token: str,
) -> RepoRecommendationResponse:
    """Run the Repository Recommendation Agent, tiered by experience level.

    The agent's proposals are verified against live GitHub data and re-scored before
    being trusted; if fewer than MIN_REPO_RESULTS survive, the deterministic search is
    used to top up the list rather than replace it. Results are cached in Redis for
    30 minutes, and only when non-empty — an empty or all-rejected result is never
    cached, so one bad run cannot poison every user sharing that skill profile.
    """
    cache_key = build_cache_key("repos", languages, frameworks, domains, experience_level)
    cached = await cache_get(cache_key)
    if cached:
        logger.info("Returning cached repo recommendations")
        return RepoRecommendationResponse(**cached)

    tier = ExperienceTier.from_experience_level(experience_level)
    suggested_query = build_repo_query(tier, language=(languages[0] if languages else ""))

    message = (
        f"Find open source repositories for a developer with these skills:\n"
        f"- Languages: {', '.join(languages)}\n"
        f"- Frameworks: {', '.join(frameworks)}\n"
        f"- Experience Level: {experience_level} (tier: {tier.value})\n"
        f"- Domains: {', '.join(domains)}\n"
        f"Suggested starting query for this developer's tier: {suggested_query}\n"
        f"Return recommendations as a JSON object with a 'repositories' key."
    )

    result: RepoRecommendationResponse
    try:
        agent = build_repo_agent(github_token)
        response = await _run_agent(agent, message, f"repos-{'-'.join(languages)}")
        data = _parse_json_response(response)
        parsed = RepoRecommendationResponse(**data)
        if not parsed.repositories:
            raise RuntimeError("Repo agent returned zero repositories")

        verified = await _verify_recommended_repos(
            parsed.repositories, tier, languages, frameworks, domains, github_token
        )
        if len(verified) >= MIN_REPO_RESULTS:
            result = RepoRecommendationResponse(repositories=verified, source="agent")
        else:
            supplement = await _deterministic_repo_recommendation(
                languages=languages, frameworks=frameworks, domains=domains,
                experience_level=experience_level, github_token=github_token,
            )
            merged = _merge_repos_by_full_name(verified, supplement.repositories)[:MAX_REPO_RESULTS]
            result = RepoRecommendationResponse(repositories=merged, source="hybrid")
    except Exception as e:
        logger.warning("Repo agent failed (%s); using GitHub fallback: %s", type(e).__name__, str(e))
        result = await _deterministic_repo_recommendation(
            languages=languages, frameworks=frameworks, domains=domains,
            experience_level=experience_level, github_token=github_token,
        )

    if result.repositories:
        await cache_set(cache_key, result.model_dump(), ttl_seconds=1800)

    return result


async def run_issue_discovery(
    repositories: list[str],
    languages: list[str],
    experience_level: str,
    github_token: str,
) -> IssueDiscoveryResponse:
    """Run the Issue Discovery Agent, tiered by experience level.

    Results are cached in Redis for 15 minutes (issues change frequently), and only
    when non-empty.
    """
    cache_key = build_cache_key("issues", repositories, languages, experience_level)
    cached = await cache_get(cache_key)
    if cached:
        logger.info("Returning cached issue recommendations")
        return IssueDiscoveryResponse(**cached)

    tier = ExperienceTier.from_experience_level(experience_level)

    message = (
        f"Find issues in these repositories, spreading results across all of them:\n"
        f"- Repositories: {', '.join(repositories)}\n"
        f"- Developer's languages: {', '.join(languages)}\n"
        f"- Experience level: {experience_level} (tier: {tier.value})\n"
        f"Return issues as a JSON object with an 'issues' key."
    )

    result: IssueDiscoveryResponse
    try:
        agent = build_issue_agent(github_token)
        response = await _run_agent(agent, message, "issues-discover")
        data = _parse_json_response(response)
        parsed = IssueDiscoveryResponse(**data)
        if not parsed.issues:
            raise RuntimeError("Issue agent returned zero issues")

        verified = await _verify_discovered_issues(parsed.issues, tier, languages, github_token)
        if len(verified) >= 3:
            result = IssueDiscoveryResponse(issues=verified, source="agent")
        else:
            supplement = await _deterministic_issue_discovery(
                repositories=repositories, languages=languages,
                experience_level=experience_level, github_token=github_token,
            )
            merged = _merge_issues_by_key(verified, supplement.issues)[:MAX_ISSUE_RESULTS]
            result = IssueDiscoveryResponse(issues=merged, source="hybrid")
    except Exception as e:
        logger.warning("Issue agent failed (%s); using GitHub fallback: %s", type(e).__name__, str(e))
        result = await _deterministic_issue_discovery(
            repositories=repositories, languages=languages,
            experience_level=experience_level, github_token=github_token,
        )

    if result.issues:
        await cache_set(cache_key, result.model_dump(), ttl_seconds=900)

    return result


async def run_issue_explanation(
    owner: str,
    repo: str,
    issue_number: int,
    github_token: str,
) -> IssueExplanationResponse:
    """Run the Issue Explainer Agent.

    Results are cached in Redis for 2 hours (explanations are stable).
    """
    cache_key = build_cache_key("explain", f"{owner}/{repo}", str(issue_number))
    cached = await cache_get(cache_key)
    if cached:
        logger.info("Returning cached issue explanation for %s/%s#%d", owner, repo, issue_number)
        return IssueExplanationResponse(**cached)

    message = (
        f"Explain the GitHub issue #{issue_number} in the repository '{owner}/{repo}'.\n"
        f"Fetch the issue details and the repository README for context.\n"
        f"Return the explanation as a structured JSON object."
    )

    try:
        agent = build_explainer_agent(github_token)
        response = await _run_agent(agent, message, f"explain-{owner}-{repo}-{issue_number}")
        data = _parse_json_response(response)
        result = IssueExplanationResponse(**data)
    except Exception as e:
        logger.warning("Issue explainer failed (%s); using GitHub fallback: %s", type(e).__name__, str(e))
        result = await _fallback_issue_explanation(
            owner=owner,
            repo=repo,
            issue_number=issue_number,
            github_token=github_token,
        )

    if result.title:
        await cache_set(cache_key, result.model_dump(), ttl_seconds=7200)

    return result

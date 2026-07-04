"""Coordinator Agent — orchestrates all sub-agents and manages the mentoring workflow.

The Coordinator is the root agent in the ADK hierarchy. It receives user requests,
delegates to specialized sub-agents (Profile, Repo, Issue, Explainer), and
aggregates their responses into a unified result.
"""

import asyncio
import json
import logging
import re

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agents.profile_agent import profile_agent
from app.agents.repo_agent import repo_agent
from app.agents.issue_agent import issue_agent
from app.agents.explainer_agent import explainer_agent
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
    fetch_repo_readme,
    fetch_user_repos,
    search_github_issues,
    search_github_repos,
)
from app.tools.utils import cache_get, cache_set, truncate_text

logger = logging.getLogger(__name__)

COORDINATOR_INSTRUCTION = """You are the AgentCommit Coordinator — the central orchestrator
for an AI-powered open source mentoring platform.

You manage a team of specialized agents:
1. Profile Analyzer — analyzes GitHub profiles
2. Repository Recommender — finds matching repos
3. Issue Discoverer — finds beginner-friendly issues
4. Issue Explainer — explains issues in plain English

When you receive a task, delegate it to the appropriate sub-agent.
Always return the sub-agent's structured response without modification.
If a sub-agent fails, provide a helpful error message.
"""

coordinator_agent = Agent(
    name="coordinator",
    model="gemini-2.5-flash",
    instruction=COORDINATOR_INSTRUCTION,
    sub_agents=[profile_agent, repo_agent, issue_agent, explainer_agent],
)

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


def _fallback_repo_from_github(repo: dict, match_score: float, match_reason: str) -> RecommendedRepo | None:
    full_name = _repo_full_name(repo)
    if not full_name:
        return None

    return RecommendedRepo(
        full_name=full_name,
        description=repo.get("description") or "",
        stars=int(repo.get("stargazers_count") or 0),
        language=repo.get("language") or "",
        topics=repo.get("topics") or [],
        open_issues_count=int(repo.get("open_issues_count") or 0),
        html_url=repo.get("html_url") or "",
        match_score=match_score,
        match_reason=match_reason,
    )


def _fallback_issue_from_github(issue: dict, repo_full_name: str, match_score: float) -> DiscoveredIssue | None:
    if "pull_request" in issue:
        return None

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
    label_text = " ".join(labels).lower()
    difficulty = "easy" if any(term in label_text for term in ["good first", "docs", "documentation"]) else "medium"

    return DiscoveredIssue(
        title=title,
        number=number,
        repo_full_name=repo_full_name,
        labels=labels,
        html_url=issue.get("html_url") or "",
        created_at=issue.get("created_at") or "",
        comments=int(issue.get("comments") or 0),
        body_preview=truncate_text(body, 200) if body else "",
        difficulty=difficulty,
        match_score=match_score,
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


async def _fallback_repo_recommendation(
    languages: list[str],
    frameworks: list[str],
    domains: list[str],
    github_token: str,
) -> RepoRecommendationResponse:
    """Recommend repositories from GitHub search when the agent does not return JSON."""
    search_terms = languages[:3] or frameworks[:3] or domains[:2] or ["javascript"]
    recommended: list[RecommendedRepo] = []
    seen: set[str] = set()

    for term in search_terms:
        query = f"language:{term} good-first-issues:>2 stars:>50 archived:false"
        repos = await search_github_repos(query, github_token, per_page=5)
        for repo in repos:
            if repo.get("error"):
                continue
            full_name = _repo_full_name(repo)
            if not full_name or full_name in seen:
                continue

            seen.add(full_name)
            match_score = max(60.0, 95.0 - (len(recommended) * 5.0))
            fallback_repo = _fallback_repo_from_github(
                repo,
                match_score=match_score,
                match_reason=f"Matches the developer profile through {term} and has open beginner-friendly issues.",
            )
            if fallback_repo:
                recommended.append(fallback_repo)

            if len(recommended) >= 10:
                return RepoRecommendationResponse(repositories=recommended)

    return RepoRecommendationResponse(repositories=recommended)


async def _fallback_issue_discovery(
    repositories: list[str],
    github_token: str,
) -> IssueDiscoveryResponse:
    """Discover issues directly from GitHub labels when the agent is unavailable."""
    label_queries = ["good first issue", "help wanted", "documentation"]
    discovered: list[DiscoveredIssue] = []
    seen: set[str] = set()

    for repo_full_name in repositories:
        for labels in label_queries:
            issues = await search_github_issues(
                repo_full_name=repo_full_name,
                github_token=github_token,
                labels=labels,
                per_page=5,
            )
            for issue in issues:
                if issue.get("error"):
                    continue
                issue_key = f"{repo_full_name}#{issue.get('number')}"
                if issue_key in seen:
                    continue

                seen.add(issue_key)
                match_score = max(55.0, 95.0 - (len(discovered) * 4.0))
                fallback_issue = _fallback_issue_from_github(issue, repo_full_name, match_score)
                if fallback_issue:
                    discovered.append(fallback_issue)

                if len(discovered) >= 10:
                    return IssueDiscoveryResponse(issues=discovered)

    return IssueDiscoveryResponse(issues=discovered)


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
    label_text = " ".join(labels).lower()
    difficulty = 1 if any(term in label_text for term in ["good first", "docs", "documentation"]) else 3
    concepts = _ordered_unique(labels + ["GitHub issues", f"{owner}/{repo} project context"])[:6]
    readme_hint = " Review the project README for setup and contribution context." if readme else ""

    return IssueExplanationResponse(
        title=issue.get("title") or f"{owner}/{repo} issue #{issue_number}",
        summary=truncate_text(body, 700),
        difficulty=difficulty,
        estimated_time="1-3 hours" if difficulty <= 2 else "3-6 hours",
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


async def run_profile_analysis(
    username: str,
    github_token: str,
) -> ProfileAnalysisResponse:
    """Run the Profile Analyzer Agent for a given GitHub user.

    Results are cached in Redis for 1 hour.
    """
    cache_key = f"profile:{username}"
    cached = await cache_get(cache_key)
    if cached:
        logger.info("Returning cached profile analysis for %s", username)
        return ProfileAnalysisResponse(**cached)

    message = (
        f"Analyze the GitHub profile for user '{username}'. "
        f"Use the github_token '{github_token}' when calling tools. "
        f"Return the analysis as a structured JSON object."
    )

    try:
        response = await _run_agent(profile_agent, message, f"profile-{username}")
        data = _parse_json_response(response)
        result = ProfileAnalysisResponse(**data)
    except Exception as e:
        logger.warning("Profile agent failed; using GitHub fallback: %s", str(e))
        result = await _fallback_profile_analysis(username, github_token)

    # Cache for 1 hour
    await cache_set(cache_key, result.model_dump(), ttl_seconds=3600)

    return result


async def run_repo_recommendation(
    languages: list[str],
    frameworks: list[str],
    experience_level: str,
    domains: list[str],
    github_token: str,
) -> RepoRecommendationResponse:
    """Run the Repository Recommendation Agent.

    Results are cached in Redis for 30 minutes.
    """
    cache_key = f"repos:{'-'.join(sorted(languages))}:{experience_level}"
    cached = await cache_get(cache_key)
    if cached:
        logger.info("Returning cached repo recommendations")
        return RepoRecommendationResponse(**cached)

    message = (
        f"Find open source repositories for a developer with these skills:\n"
        f"- Languages: {', '.join(languages)}\n"
        f"- Frameworks: {', '.join(frameworks)}\n"
        f"- Experience Level: {experience_level}\n"
        f"- Domains: {', '.join(domains)}\n"
        f"Use the github_token '{github_token}' when calling search tools.\n"
        f"Return recommendations as a JSON object with a 'repositories' key."
    )

    try:
        response = await _run_agent(repo_agent, message, f"repos-{'-'.join(languages)}")
        data = _parse_json_response(response)
        result = RepoRecommendationResponse(**data)
    except Exception as e:
        logger.warning("Repo agent failed; using GitHub fallback: %s", str(e))
        result = await _fallback_repo_recommendation(
            languages=languages,
            frameworks=frameworks,
            domains=domains,
            github_token=github_token,
        )

    # Cache for 30 minutes
    await cache_set(cache_key, result.model_dump(), ttl_seconds=1800)

    return result


async def run_issue_discovery(
    repositories: list[str],
    languages: list[str],
    experience_level: str,
    github_token: str,
) -> IssueDiscoveryResponse:
    """Run the Issue Discovery Agent.

    Results are cached in Redis for 15 minutes (issues change frequently).
    """
    cache_key = f"issues:{'-'.join(sorted(repositories[:3]))}:{experience_level}"
    cached = await cache_get(cache_key)
    if cached:
        logger.info("Returning cached issue recommendations")
        return IssueDiscoveryResponse(**cached)

    message = (
        f"Find beginner-friendly issues in these repositories:\n"
        f"- Repositories: {', '.join(repositories)}\n"
        f"- Developer's languages: {', '.join(languages)}\n"
        f"- Experience level: {experience_level}\n"
        f"Use the github_token '{github_token}' when calling tools.\n"
        f"Return issues as a JSON object with an 'issues' key."
    )

    try:
        response = await _run_agent(issue_agent, message, f"issues-discover")
        data = _parse_json_response(response)
        result = IssueDiscoveryResponse(**data)
    except Exception as e:
        logger.warning("Issue agent failed; using GitHub fallback: %s", str(e))
        result = await _fallback_issue_discovery(
            repositories=repositories,
            github_token=github_token,
        )

    # Cache for 15 minutes
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
    cache_key = f"explain:{owner}/{repo}#{issue_number}"
    cached = await cache_get(cache_key)
    if cached:
        logger.info("Returning cached issue explanation for %s/%s#%d", owner, repo, issue_number)
        return IssueExplanationResponse(**cached)

    message = (
        f"Explain the GitHub issue #{issue_number} in the repository '{owner}/{repo}'.\n"
        f"Use the github_token '{github_token}' when calling tools.\n"
        f"Fetch the issue details and the repository README for context.\n"
        f"Return the explanation as a structured JSON object."
    )

    try:
        response = await _run_agent(explainer_agent, message, f"explain-{owner}-{repo}-{issue_number}")
        data = _parse_json_response(response)
        result = IssueExplanationResponse(**data)
    except Exception as e:
        logger.warning("Issue explainer failed; using GitHub fallback: %s", str(e))
        result = await _fallback_issue_explanation(
            owner=owner,
            repo=repo,
            issue_number=issue_number,
            github_token=github_token,
        )

    # Cache for 2 hours
    await cache_set(cache_key, result.model_dump(), ttl_seconds=7200)

    return result

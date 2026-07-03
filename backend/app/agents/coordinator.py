"""Coordinator Agent — orchestrates all sub-agents and manages the mentoring workflow.

The Coordinator is the root agent in the ADK hierarchy. It receives user requests,
delegates to specialized sub-agents (Profile, Repo, Issue, Explainer), and
aggregates their responses into a unified result.
"""

import json
import logging

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
    IssueDiscoveryResponse,
    IssueExplanationResponse,
)
from app.tools.utils import cache_get, cache_set

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
    model="gemini-2.5-pro",
    instruction=COORDINATOR_INSTRUCTION,
    sub_agents=[profile_agent, repo_agent, issue_agent, explainer_agent],
)

# Session service for managing agent conversations
session_service = InMemorySessionService()


async def _run_agent(
    agent: Agent,
    user_message: str,
    session_id: str,
) -> str:
    """Run an ADK agent with a user message and return the text response.

    Args:
        agent: The ADK agent to run.
        user_message: The message/instruction to send.
        session_id: Unique session identifier.

    Returns:
        The agent's text response.
    """
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
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response


def _parse_json_response(response: str) -> dict:
    """Extract and parse JSON from an agent's response text.

    The agent may wrap JSON in markdown code blocks.
    """
    text = response.strip()

    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (``` markers)
        lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(lines)

    return json.loads(text)


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

    response = await _run_agent(profile_agent, message, f"profile-{username}")
    data = _parse_json_response(response)

    result = ProfileAnalysisResponse(**data)

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

    response = await _run_agent(repo_agent, message, f"repos-{'-'.join(languages)}")
    data = _parse_json_response(response)

    result = RepoRecommendationResponse(**data)

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

    response = await _run_agent(issue_agent, message, f"issues-discover")
    data = _parse_json_response(response)

    result = IssueDiscoveryResponse(**data)

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

    response = await _run_agent(explainer_agent, message, f"explain-{owner}-{repo}-{issue_number}")
    data = _parse_json_response(response)

    result = IssueExplanationResponse(**data)

    # Cache for 2 hours
    await cache_set(cache_key, result.model_dump(), ttl_seconds=7200)

    return result

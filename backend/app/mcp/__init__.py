"""GitHub MCP server integration for AgentCommit.

Wraps the GitHub MCP server to provide agents with enhanced GitHub
capabilities through the Model Context Protocol.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import settings

logger = logging.getLogger(__name__)


def get_github_mcp_params() -> StdioServerParameters:
    """Create parameters for the GitHub MCP server process."""
    return StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={
            "GITHUB_PERSONAL_ACCESS_TOKEN": settings.github_mcp_token,
        },
    )


@asynccontextmanager
async def get_github_mcp_session() -> AsyncGenerator[ClientSession, None]:
    """Create and manage a GitHub MCP client session.

    Usage:
        async with get_github_mcp_session() as session:
            result = await session.call_tool("search_repositories", {"query": "..."})
    """
    server_params = get_github_mcp_params()

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info("GitHub MCP session initialized")
            yield session


async def mcp_search_repositories(query: str, per_page: int = 10) -> list[dict]:
    """Search repositories using the GitHub MCP server.

    Args:
        query: Search query string.
        per_page: Number of results.

    Returns:
        List of repository data from MCP.
    """
    async with get_github_mcp_session() as session:
        result = await session.call_tool(
            "search_repositories",
            {"query": query, "perPage": per_page},
        )
        return result.content if result.content else []


async def mcp_get_file_contents(owner: str, repo: str, path: str) -> str:
    """Fetch file contents from a repository using GitHub MCP.

    Args:
        owner: Repository owner.
        repo: Repository name.
        path: File path within the repo.

    Returns:
        File content as string.
    """
    async with get_github_mcp_session() as session:
        result = await session.call_tool(
            "get_file_contents",
            {"owner": owner, "repo": repo, "path": path},
        )
        return str(result.content[0].text) if result.content else ""


async def mcp_list_issues(
    owner: str,
    repo: str,
    labels: list[str] | None = None,
    state: str = "open",
    per_page: int = 10,
) -> list[dict]:
    """List issues in a repository using GitHub MCP.

    Args:
        owner: Repository owner.
        repo: Repository name.
        labels: Optional list of label names to filter.
        state: Issue state filter.
        per_page: Number of results.

    Returns:
        List of issue data from MCP.
    """
    params: dict = {
        "owner": owner,
        "repo": repo,
        "state": state,
        "perPage": per_page,
    }
    if labels:
        params["labels"] = labels

    async with get_github_mcp_session() as session:
        result = await session.call_tool("list_issues", params)
        return result.content if result.content else []

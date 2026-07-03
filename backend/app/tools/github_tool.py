"""GitHub API tool functions for use by ADK agents.

Each function is designed to be registered as a Google ADK FunctionTool,
providing agents with the ability to interact with the GitHub REST API.
"""

import httpx

GITHUB_API_BASE = "https://api.github.com"


async def fetch_github_profile(username: str, github_token: str) -> dict:
    """Fetch a GitHub user's profile information.

    Args:
        username: GitHub username to look up.
        github_token: OAuth access token for authentication.

    Returns:
        Dictionary containing the user's profile data.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/users/{username}",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        response.raise_for_status()
        return response.json()


async def fetch_user_repos(
    username: str,
    github_token: str,
    sort: str = "updated",
    per_page: int = 30,
) -> list[dict]:
    """Fetch repositories for a GitHub user.

    Args:
        username: GitHub username.
        github_token: OAuth access token.
        sort: Sort field — 'created', 'updated', 'pushed', 'full_name'.
        per_page: Number of results per page (max 100).

    Returns:
        List of repository data dictionaries.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/users/{username}/repos",
            params={"sort": sort, "per_page": per_page, "type": "owner"},
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        response.raise_for_status()
        return response.json()


async def search_github_repos(
    query: str,
    github_token: str,
    sort: str = "stars",
    per_page: int = 10,
) -> list[dict]:
    """Search GitHub repositories by query string.

    Args:
        query: Search query (e.g., 'language:python topic:machine-learning stars:>100').
        github_token: OAuth access token.
        sort: Sort field — 'stars', 'forks', 'help-wanted-issues', 'updated'.
        per_page: Number of results.

    Returns:
        List of matching repository data.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/search/repositories",
            params={"q": query, "sort": sort, "per_page": per_page},
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])


async def search_github_issues(
    repo_full_name: str,
    github_token: str,
    labels: str = "good first issue",
    state: str = "open",
    per_page: int = 10,
) -> list[dict]:
    """Search for issues in a specific repository.

    Args:
        repo_full_name: Repository in 'owner/repo' format.
        github_token: OAuth access token.
        labels: Comma-separated labels to filter by.
        state: Issue state — 'open', 'closed', 'all'.
        per_page: Number of results.

    Returns:
        List of issue data dictionaries.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues",
            params={
                "labels": labels,
                "state": state,
                "per_page": per_page,
                "sort": "created",
                "direction": "desc",
            },
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        response.raise_for_status()
        return response.json()


async def fetch_issue_details(
    owner: str,
    repo: str,
    issue_number: int,
    github_token: str,
) -> dict:
    """Fetch detailed information about a specific GitHub issue.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue number.
        github_token: OAuth access token.

    Returns:
        Dictionary containing the issue details.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        response.raise_for_status()
        return response.json()


async def fetch_repo_readme(
    owner: str,
    repo: str,
    github_token: str,
) -> str:
    """Fetch the README content of a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        github_token: OAuth access token.

    Returns:
        README content as a string, or empty string if not found.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.raw+json",
            },
        )
        if response.status_code == 404:
            return ""
        response.raise_for_status()
        return response.text


async def fetch_repo_languages(
    owner: str,
    repo: str,
    github_token: str,
) -> dict:
    """Fetch language breakdown for a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        github_token: OAuth access token.

    Returns:
        Dictionary mapping language names to byte counts.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/languages",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        response.raise_for_status()
        return response.json()

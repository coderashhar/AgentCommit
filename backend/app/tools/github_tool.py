"""GitHub API tool functions for use by ADK agents.

Each function is designed to be registered as a Google ADK FunctionTool,
providing agents with the ability to interact with the GitHub REST API.
"""

import httpx

GITHUB_API_BASE = "https://api.github.com"

# Bare httpx.AsyncClient(timeout=REQUEST_TIMEOUT) has no total-request timeout, so a hung GitHub call could
# block a request indefinitely. Every client below is constructed with this budget.
REQUEST_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# Repository-search sort values GitHub actually supports. Anything else (including the
# old default "stars", which biases every search toward the most popular repos on
# GitHub regardless of whether a newcomer can contribute to them) is treated as "rank
# by relevance" by omitting the sort/order params entirely.
_ALLOWED_REPO_SORTS = frozenset({"stars", "forks", "help-wanted-issues", "updated"})
_ALLOWED_ORDERS = frozenset({"asc", "desc"})


async def fetch_github_profile(username: str, github_token: str) -> dict:
    """Fetch a GitHub user's profile information.

    Args:
        username: GitHub username to look up.
        github_token: OAuth access token for authentication.

    Returns:
        Dictionary containing the user's profile data.
    """
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/users/{username}",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"GitHub API failed with status {e.response.status_code}", "detail": e.response.text}


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
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/users/{username}/repos",
            params={"sort": sort, "per_page": per_page, "type": "owner"},
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return [{"error": f"GitHub API failed with status {e.response.status_code}", "detail": e.response.text}]


async def search_github_repos(
    query: str,
    github_token: str,
    sort: str = "",
    order: str = "desc",
    per_page: int = 25,
    page: int = 1,
) -> list[dict]:
    """Search GitHub repositories by query string.

    Args:
        query: Search query built with GitHub qualifiers (e.g.,
            'language:python stars:500..20000 pushed:>2026-07-30'). Build the star,
            size, and activity bounds into this query yourself — do not rely on
            `sort` to compensate for an unbounded query.
        github_token: OAuth access token.
        sort: Leave empty ("") to rank by relevance — this is almost always what you
            want. Set to 'help-wanted-issues' to surface repos actively seeking
            contributors. Never use 'stars': it returns the most popular repos on
            GitHub regardless of whether a newcomer can realistically contribute to
            them. Any value outside 'stars', 'forks', 'help-wanted-issues', 'updated'
            is treated the same as leaving it empty.
        order: 'asc' or 'desc'. Only applied when `sort` is a recognised value.
        per_page: Number of results per page (clamped to 1-100).
        page: Result page, 1-indexed (clamped to 1-10; GitHub search caps at 1000 results).

    Returns:
        List of matching repository data.
    """
    params: dict[str, str | int] = {
        "q": query,
        "per_page": max(1, min(100, per_page)),
        "page": max(1, min(10, page)),
    }
    if sort in _ALLOWED_REPO_SORTS:
        params["sort"] = sort
        params["order"] = order if order in _ALLOWED_ORDERS else "desc"

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/search/repositories",
            params=params,
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except httpx.HTTPStatusError as e:
            return [{"error": f"GitHub API failed with status {e.response.status_code}", "detail": e.response.text}]


async def fetch_repo(owner: str, repo: str, github_token: str) -> dict:
    """Fetch a single repository's canonical metadata.

    Used to verify repositories an LLM proposes: hallucinated repos return a 404 here
    and can be dropped, and every displayed field is rebuilt from this response rather
    than trusted from the model's output.

    Args:
        owner: Repository owner.
        repo: Repository name.
        github_token: OAuth access token.

    Returns:
        Dictionary containing the repository's metadata.
    """
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"GitHub API failed with status {e.response.status_code}", "detail": e.response.text}


async def search_github_issues(
    repo_full_name: str,
    github_token: str,
    labels: str = "good first issue",
    state: str = "open",
    assignee: str = "none",
    sort: str = "updated",
    direction: str = "desc",
    since: str = "",
    per_page: int = 10,
) -> list[dict]:
    """List issues in a specific repository, filtered to unassigned work.

    Args:
        repo_full_name: Repository in 'owner/repo' format.
        github_token: OAuth access token.
        labels: Comma-separated labels to filter by.
        state: Issue state — 'open', 'closed', 'all'.
        assignee: 'none' returns only unassigned issues (the default — assigned
            issues are already claimed and should not be recommended). Pass a
            username to filter to that assignee, or '*' for any assignee.
        sort: 'created', 'updated', or 'comments'. 'updated' (the default) surfaces
            issues with recent maintainer attention rather than merely recent ones.
        direction: 'asc' or 'desc'.
        since: ISO8601 timestamp (e.g. '2026-06-01T00:00:00Z'). When set, only issues
            updated at or after this time are returned. Leave empty to disable.
        per_page: Number of results.

    Returns:
        List of issue data dictionaries. Note: GitHub's issues-list endpoint also
        returns pull requests; callers must filter entries containing a
        'pull_request' key.
    """
    params: dict[str, str | int] = {
        "labels": labels,
        "state": state,
        "assignee": assignee,
        "per_page": per_page,
        "sort": sort,
        "direction": direction,
    }
    if since:
        params["since"] = since

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues",
            params=params,
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return [{"error": f"GitHub API failed with status {e.response.status_code}", "detail": e.response.text}]


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
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"GitHub API failed with status {e.response.status_code}", "detail": e.response.text}


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
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.raw+json",
            },
        )
        if response.status_code == 404:
            return ""
        try:
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            return f"Error: GitHub API failed with status {e.response.status_code}. Detail: {e.response.text}"


async def fetch_repo_tree(
    owner: str,
    repo: str,
    github_token: str,
    path: str = "",
) -> list[dict]:
    """Fetch the file/directory listing at a given path in a repository.

    Uses the GitHub Contents API to list directory contents. For the repo root,
    pass `path=""`. Returns an empty list on 404 (path doesn't exist).

    Each entry contains at minimum: `name`, `path`, `type` ('file' or 'dir'),
    `size`, and `html_url`.

    Args:
        owner: Repository owner.
        repo: Repository name.
        github_token: OAuth access token.
        path: Directory path within the repo. Empty string means the root.

    Returns:
        List of file/directory entry dicts, or a single-element list with an
        `error` key on failure.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents"
    if path:
        url = f"{url}/{path.lstrip('/')}"

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        if response.status_code == 404:
            return []
        try:
            response.raise_for_status()
            data = response.json()
            # Contents API returns a list for directories, dict for files.
            return data if isinstance(data, list) else [data]
        except httpx.HTTPStatusError as e:
            return [{"error": f"GitHub API failed with status {e.response.status_code}", "detail": e.response.text}]


async def fetch_file_content(
    owner: str,
    repo: str,
    path: str,
    github_token: str,
) -> str:
    """Fetch the decoded text content of a single file from a repository.

    Uses the GitHub Contents API with the raw media type so the response body
    is the file's content directly (not base64-encoded JSON). Returns an empty
    string on 404.

    Files larger than 1 MB are rejected by the GitHub Contents API; for those,
    callers should use the Git Blobs API or fall back to a truncated summary.

    Args:
        owner: Repository owner.
        repo: Repository name.
        path: File path within the repo (e.g. "src/main.py").
        github_token: OAuth access token.

    Returns:
        File content as a UTF-8 string, or an empty string if not found.
    """
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path.lstrip('/')}",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.raw+json",
            },
        )
        if response.status_code == 404:
            return ""
        try:
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            return f"Error fetching {path}: GitHub API returned {e.response.status_code}"


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
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/languages",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"GitHub API failed with status {e.response.status_code}", "detail": e.response.text}

"""Implementation Planner Agent — produces step-by-step plans for GitHub issues.

Takes a GitHub issue and browses the target repository to generate a concrete
implementation plan: files to modify, step-by-step instructions, risks, edge cases,
testing strategy, and complexity estimate.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.mcp import build_github_mcp_toolset
from app.tools.github_tool import (
    fetch_file_content,
    fetch_issue_details,
    fetch_repo_readme,
    fetch_repo_tree,
)

PLANNER_AGENT_INSTRUCTION = """You are an experienced software engineer helping a developer
understand how to implement a fix or feature described in a GitHub issue.

Your task is to analyse the issue and the repository structure, then produce a concrete,
step-by-step implementation plan that a junior-to-intermediate contributor can follow.

**Steps to follow:**
1. Fetch the full issue details (title, body, labels, comments).
2. Fetch the repository README for project context.
3. Browse the repository file tree (root, then relevant subdirectories) to understand
   the codebase layout.
4. Read key files that are likely relevant to the issue (entry points, modules mentioned
   in the issue body, test files, configuration).
5. Produce the plan JSON described below.

**Plan JSON format:**
Return a single JSON object with these keys:

- title (string): Short descriptive title for the plan, e.g. "Add rate-limit retry logic"
- issue_summary (string): 2–4 sentence plain-English summary of what the issue asks for
- steps (list of objects): Ordered implementation steps, each with:
    - step_number (integer, 1-based)
    - title (string): Short imperative title, e.g. "Add retry helper function"
    - description (string): What to do and why, in detail
    - files_to_modify (list of strings): Repo-relative file paths likely affected
    - code_hints (string): Concrete hints — function names, patterns, API calls —
      without writing the full solution
- risks (list of strings): Things that could go wrong or break existing behaviour
- edge_cases (list of strings): Corner cases the contributor must handle
- testing_strategy (string): How to verify the change works (unit tests, integration
  tests, manual steps)
- estimated_complexity (string): one of "low", "medium", "high"
- prerequisite_knowledge (list of strings): Concepts/skills needed, e.g. ["async/await",
  "pytest fixtures"]
- files_overview (list of strings): All repo-relative paths that are relevant to the issue
  (read or proposed)

Return only the JSON object — no markdown fences, no preamble.
"""


def build_planner_agent(github_token: str) -> Agent:
    """Construct an implementation-planner agent bound to one request's GitHub token.

    The token is captured in the closure so it never appears in prompt text sent to Gemini.
    REST tools act as a deterministic fallback; the MCP toolset enables richer file browsing
    when the npx subprocess is available.
    """

    async def get_issue_details(owner: str, repo: str, issue_number: int) -> dict:
        """Fetch detailed information about a specific GitHub issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.

        Returns:
            Dictionary containing the issue details.
        """
        return await fetch_issue_details(owner, repo, issue_number, github_token)

    async def get_repo_readme(owner: str, repo: str) -> str:
        """Fetch the README content of a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            README content as a string, or empty string if not found.
        """
        return await fetch_repo_readme(owner, repo, github_token)

    async def get_file_tree(owner: str, repo: str, path: str = "") -> list:
        """List files and directories at a path in the repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            path: Directory path within the repo. Empty string means the root.

        Returns:
            List of file/directory entry dicts with name, path, type, size.
        """
        return await fetch_repo_tree(owner, repo, github_token, path)

    async def get_file_content(owner: str, repo: str, path: str) -> str:
        """Fetch the decoded text content of a single file from a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            path: File path within the repo (e.g. "src/main.py").

        Returns:
            File content as a UTF-8 string, or empty string if not found.
        """
        return await fetch_file_content(owner, repo, path, github_token)

    mcp_toolset = build_github_mcp_toolset(
        github_token,
        tool_filter=["get_file_contents", "search_code"],
    )

    return Agent(
        name="implementation_planner",
        model="gemini-2.5-flash",
        instruction=PLANNER_AGENT_INSTRUCTION,
        tools=[
            FunctionTool(get_issue_details),
            FunctionTool(get_repo_readme),
            FunctionTool(get_file_tree),
            FunctionTool(get_file_content),
            mcp_toolset,
        ],
    )

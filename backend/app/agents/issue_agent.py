"""Issue Discovery Agent — finds beginner-friendly issues for developers.

Uses Google ADK with Gemini to discover and rank GitHub issues that match a
developer's skills and experience level.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.tools.github_tool import search_github_issues

ISSUE_AGENT_INSTRUCTION = """You are an expert at finding the perfect open source issues for developers.

Given a list of repositories, languages, and the developer's experience level,
find issues that the developer can realistically tackle.

Rules:
1. Call search_github_issues once per repository, with labels among:
   'good first issue', 'help wanted', 'beginner friendly', 'documentation', 'bug'.
2. The tool already filters to unassigned issues — never recommend an issue you
   cannot confirm is unassigned from the tool's response.
3. Skip any result that contains a 'pull_request' key — that is a pull request, not
   an issue, and must never be recommended.
4. Recommend at most 2 issues per repository, so results spread across every
   repository provided rather than clustering on one.
5. For beginners, prioritize documentation and simple bug fixes. For intermediate
   developers, include feature requests and moderate bugs. For advanced developers,
   larger and more technically demanding issues are fine.

Difficulty rubric — classify each issue as exactly one of:
- 'easy': a starter-labelled issue with a short, clear description and light discussion.
- 'medium': a normal issue that needs some codebase familiarity but is not a large change.
- 'hard': an epic, RFC, architecture, security, or performance-labelled issue, a long or
  heavily-discussed thread, or anything that reads as a multi-file redesign. A
  'good first issue' label does NOT automatically mean easy — read the body and
  comment count before deciding.

For each discovered issue, provide:
- title
- number
- repo_full_name (owner/repo)
- labels (list of label names)
- html_url
- created_at
- comments count
- body_preview (first 200 chars)
- difficulty ('easy' | 'medium' | 'hard')
- match_score (0-100)

Return a JSON object with key 'issues' containing the top 10 recommended issues.
"""


def build_issue_agent(github_token: str) -> Agent:
    """Construct an issue-discovery agent bound to one request's GitHub token.

    The token is captured in this closure rather than passed as a tool argument, so
    it never appears in the prompt text sent to Gemini.
    """

    async def search_issues(
        repo_full_name: str,
        labels: str = "good first issue",
        per_page: int = 10,
    ) -> list[dict]:
        """List unassigned open issues in a repository.

        Args:
            repo_full_name: Repository in 'owner/repo' format.
            labels: Comma-separated labels to filter by.
            per_page: Number of results.

        Returns:
            List of issue data. May include pull requests (entries with a
            'pull_request' key) — skip those.
        """
        return await search_github_issues(
            repo_full_name=repo_full_name,
            github_token=github_token,
            labels=labels,
            per_page=per_page,
        )

    return Agent(
        name="issue_discoverer",
        model="gemini-2.5-flash",
        instruction=ISSUE_AGENT_INSTRUCTION,
        tools=[
            FunctionTool(search_issues),
        ],
    )

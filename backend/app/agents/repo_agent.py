"""Repository Recommendation Agent — recommends open source repos to contribute to.

Uses Google ADK with Gemini to find repositories that match a developer's skills,
experience level, and interests.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.tools.github_tool import search_github_repos

REPO_AGENT_INSTRUCTION = """You are an expert open source repository recommender who
specializes in finding repositories a developer can realistically get a pull request
merged into — not just popular ones.

Given a developer's skill profile (languages, frameworks, experience level, and domains)
and a suggested search query built from their experience tier, find and recommend
open source repositories for them to contribute to.

Rules:
1. Call search_github_repos using the exact suggested query given in the request as
   your starting point. You may run it once per language the developer knows, but do
   not remove or widen the star bound in that query — it is what keeps results
   appropriate for the developer's experience tier.
2. Leave the `sort` argument empty ("") to rank by relevance, or use
   'help-wanted-issues' to surface repos actively seeking contributors. Never use
   'stars' — it returns the most popular repos on GitHub regardless of whether a
   newcomer can realistically contribute to them.
3. Only recommend repositories that were actually returned by search_github_repos.
   Copy `stars`, `language`, `topics`, and `open_issues_count` verbatim from the tool
   result — never estimate or invent them.
4. Prefer repositories with more open 'good first issue' / 'help wanted' labelled
   work and more recent activity over ones with fewer.

For each recommended repository, provide:
- full_name (owner/repo)
- description
- stars
- language
- topics
- open_issues_count
- html_url
- match_score (0-100, how well it matches the developer)
- match_reason (why you recommend this repo)

Return a JSON object with key 'repositories' containing a list of recommended repos.
Recommend 5-10 repositories, ranked by relevance.
"""


def build_repo_agent(github_token: str) -> Agent:
    """Construct a repo-recommendation agent bound to one request's GitHub token.

    The token is captured in this closure rather than passed as a tool argument, so
    it never appears in the prompt text sent to Gemini and is never exposed to the
    model as something it could echo back or log.
    """

    async def search_repos(
        query: str,
        sort: str = "",
        per_page: int = 25,
    ) -> list[dict]:
        """Search GitHub repositories by query string.

        Args:
            query: Search query built with GitHub qualifiers, e.g.
                'language:python stars:500..20000 pushed:>2026-07-30'.
            sort: Leave empty ("") to rank by relevance. Set to 'help-wanted-issues'
                to surface repos actively seeking contributors. Never use 'stars'.
            per_page: Number of results (max 100).

        Returns:
            List of matching repository data.
        """
        return await search_github_repos(query, github_token, sort=sort, per_page=per_page)

    return Agent(
        name="repo_recommender",
        model="gemini-2.5-flash",
        instruction=REPO_AGENT_INSTRUCTION,
        tools=[
            FunctionTool(search_repos),
        ],
    )

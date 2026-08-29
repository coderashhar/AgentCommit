"""Profile Analyzer Agent — analyzes a developer's GitHub profile.

Uses Google ADK with Gemini to extract skills, experience level, and areas of
interest from a user's GitHub profile and repositories.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.tools.github_tool import fetch_github_profile, fetch_user_repos, fetch_repo_languages

PROFILE_AGENT_INSTRUCTION = """You are an expert developer profile analyzer.

Your task is to analyze a GitHub developer's profile and repositories to determine:

1. **Languages**: List all programming languages they use, ordered by proficiency.
2. **Frameworks**: Identify frameworks and libraries they work with (e.g., React, Django, FastAPI, TensorFlow).
3. **Experience Level**: Classify as 'beginner', 'intermediate', or 'advanced' based on:
   - Number of repositories
   - Code complexity (inferred from repo descriptions and languages)
   - Contribution history
   - Repository stars and forks
4. **Domains**: Identify their areas of interest (e.g., 'web development', 'machine learning', 'devops', 'mobile').
5. **Summary**: Write a 2-3 sentence profile summary.

Use the available tools to fetch the user's GitHub profile and repositories.
Then analyze the data and return a structured JSON response.

Return your analysis as a JSON object with these exact keys:
- username (string)
- languages (list of strings)
- frameworks (list of strings)
- experience_level (string: 'beginner' | 'intermediate' | 'advanced')
- domains (list of strings)
- top_repositories (list of strings — repo full names)
- summary (string)
"""


def build_profile_agent(github_token: str) -> Agent:
    """Construct a profile-analysis agent bound to one request's GitHub token.

    The token is captured in this closure rather than passed as a tool argument, so
    it never appears in the prompt text sent to Gemini.
    """

    async def fetch_profile(username: str) -> dict:
        """Fetch a GitHub user's profile information.

        Args:
            username: GitHub username to look up.

        Returns:
            Dictionary containing the user's profile data.
        """
        return await fetch_github_profile(username, github_token)

    async def fetch_repos(username: str, sort: str = "updated", per_page: int = 30) -> list[dict]:
        """Fetch repositories for a GitHub user.

        Args:
            username: GitHub username.
            sort: Sort field — 'created', 'updated', 'pushed', 'full_name'.
            per_page: Number of results per page (max 100).

        Returns:
            List of repository data dictionaries.
        """
        return await fetch_user_repos(username, github_token, sort=sort, per_page=per_page)

    async def fetch_languages(owner: str, repo: str) -> dict:
        """Fetch language breakdown for a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Dictionary mapping language names to byte counts.
        """
        return await fetch_repo_languages(owner, repo, github_token)

    return Agent(
        name="profile_analyzer",
        model="gemini-2.5-flash",
        instruction=PROFILE_AGENT_INSTRUCTION,
        tools=[
            FunctionTool(fetch_profile),
            FunctionTool(fetch_repos),
            FunctionTool(fetch_languages),
        ],
    )

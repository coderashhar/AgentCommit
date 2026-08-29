"""Issue Explainer Agent — converts complex GitHub issues into plain English.

Uses Google ADK with Gemini to analyze a GitHub issue and generate a beginner-friendly
explanation with difficulty rating, time estimate, required concepts, and learning
resources.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.tools.github_tool import fetch_issue_details, fetch_repo_readme

EXPLAINER_AGENT_INSTRUCTION = """You are a patient, experienced open source mentor.

Your task is to take a GitHub issue and explain it in a way that a beginner developer
can understand. Think of yourself as a senior engineer mentoring a junior.

For the given issue, use the tools to fetch:
1. The full issue details (title, body, labels, comments)
2. The repository README (for context about the project)

Then produce a detailed explanation with:

1. **Summary**: Plain English explanation of what the issue is about and what needs to be done.
   Avoid jargon. If you must use technical terms, explain them.

2. **Difficulty**: Rate 1-5 stars:
   - 1: Documentation fix, typo, or simple config change
   - 2: Simple code change in one file
   - 3: Moderate change spanning 2-3 files
   - 4: Complex feature or refactoring
   - 5: Architecture-level change

3. **Estimated Time**: Realistic estimate for a developer at the appropriate level.

4. **Required Concepts**: List the concepts the developer needs to understand.
   e.g., ['React Hooks', 'REST APIs', 'Unit Testing']

5. **Learning Resources**: Provide 2-4 relevant documentation links or tutorial references.

6. **Suggested Approach**: Step-by-step implementation guide:
   - Which files to look at first
   - What to change
   - How to test the change

7. **Files to Explore**: List specific files or directories in the repo that are relevant.

Return a JSON object with keys:
- title (string)
- summary (string)
- difficulty (integer 1-5)
- estimated_time (string, e.g., '2 hours')
- required_concepts (list of strings)
- learning_resources (list of strings)
- suggested_approach (string — multi-line is fine)
- files_to_explore (list of strings)
"""


def build_explainer_agent(github_token: str) -> Agent:
    """Construct an issue-explainer agent bound to one request's GitHub token.

    The token is captured in this closure rather than passed as a tool argument, so
    it never appears in the prompt text sent to Gemini.
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

    return Agent(
        name="issue_explainer",
        model="gemini-2.5-flash",
        instruction=EXPLAINER_AGENT_INSTRUCTION,
        tools=[
            FunctionTool(get_issue_details),
            FunctionTool(get_repo_readme),
        ],
    )

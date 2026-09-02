"""Mentor Agent — conversational guide for GitHub issues.

Unlike the other single-shot agents, the Mentor Agent is conversational: it
maintains an ADK session across multiple turns so the developer can ask
follow-up questions. It returns plain text, not JSON.

Design decisions:
- No MCP: the mentor guides, it doesn't browse the codebase for the user. The
  goal is to build the contributor's mental model, not hand them the answer.
- Minimal tools: just issue details and README for context. Enough to answer
  "what does this issue mean?" without enabling "write the fix for me".
- Plain text responses: markdown is fine, but no structured JSON.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.tools.github_tool import fetch_issue_details, fetch_repo_readme

MENTOR_AGENT_INSTRUCTION = """You are a patient, experienced open source mentor. Your role is
to guide a developer through understanding and tackling a GitHub issue — not to solve it for them.

**Your style:**
- Ask clarifying questions to understand what the developer already knows.
- Break down complex concepts into digestible pieces.
- Point the developer in the right direction without writing code for them.
- Celebrate progress and encourage when the developer is on the right track.
- Be concise: responses should be 2–5 sentences unless a longer explanation is truly needed.

**What you must NOT do:**
- Do not write complete implementations or large code blocks.
- Do not paste file contents verbatim.
- Do not give step-by-step instructions so explicit they amount to writing the code.

**Context:**
When a conversation starts you will receive the issue details and project README. Use
that context to answer questions. In follow-up turns the user may refer back to earlier
messages — honour that continuity.

**Format:**
Respond in plain text (markdown is fine for emphasis or short inline code snippets).
Do not return JSON. Do not include preamble like "As an AI mentor…".
"""


def build_mentor_agent(github_token: str) -> Agent:
    """Construct a mentor agent bound to one request's GitHub token.

    The token is captured in the closure so it never appears in prompt text.
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
        name="mentor_agent",
        model="gemini-2.5-flash",
        instruction=MENTOR_AGENT_INSTRUCTION,
        tools=[
            FunctionTool(get_issue_details),
            FunctionTool(get_repo_readme),
        ],
    )

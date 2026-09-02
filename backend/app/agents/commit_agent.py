"""Commit Message Agent — generates conventional commit messages from diffs.

Single-shot agent: takes a diff or change description and returns a structured
conventional commit message with subject, body, type, scope, and alternatives.

Design decisions:
- No MCP: diffs are self-contained; browsing the repo is not needed.
- Optional issue context: when issue_number is provided, the agent fetches the
  issue title and number to add a footer reference (e.g. "Closes #42").
- No caching: each diff is unique, so caching would never hit.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.tools.github_tool import fetch_issue_details

COMMIT_AGENT_INSTRUCTION = """You are an expert in writing conventional commit messages.

Given a diff or change description, produce a conventional commit message following
the Conventional Commits 1.0 specification (https://www.conventionalcommits.org/).

**Conventional commit format:**
```
<type>(<scope>): <short description>

[optional body]

[optional footer(s)]
```

**Types:** feat, fix, docs, style, refactor, perf, test, chore, ci, build, revert

**Rules:**
- Subject line: ≤72 characters, imperative mood, no trailing period
- Body: wrap at 72 characters, explain *what* and *why* (not how)
- Footer: "Closes #N" or "BREAKING CHANGE: <description>" when applicable
- Never use vague subjects like "update code" or "fix stuff"
- If issue context is provided, add "Closes #<number>" footer

**Your task:**
1. If issue details are provided as a tool call result, use the issue title and number.
2. Analyse the diff or change description.
3. Return a JSON object with these keys:
   - subject (string): full subject line including type and scope, ≤72 chars
   - body (string): multi-line body or empty string
   - full_message (string): subject + blank line + body (omit blank line if body is empty)
   - commit_type (string): one of the types above
   - scope (string): scope identifier or empty string
   - breaking_change (boolean): true if this introduces a breaking change
   - alternatives (list of strings): 2–3 alternative subject lines with different types or scopes

Return only the JSON object — no markdown fences, no preamble.
"""


def build_commit_agent(github_token: str) -> Agent:
    """Construct a commit-message agent bound to one request's GitHub token.

    The token is captured in the closure so it never appears in prompt text.
    """

    async def get_issue_details(owner: str, repo: str, issue_number: int) -> dict:
        """Fetch title and metadata for a GitHub issue to include in the commit footer.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.

        Returns:
            Dictionary containing the issue details.
        """
        return await fetch_issue_details(owner, repo, issue_number, github_token)

    return Agent(
        name="commit_agent",
        model="gemini-2.5-flash",
        instruction=COMMIT_AGENT_INSTRUCTION,
        tools=[
            FunctionTool(get_issue_details),
        ],
    )

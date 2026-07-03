"""Issue Discovery Agent — finds beginner-friendly issues for developers.

Uses Google ADK with Gemini 2.5 Pro to discover and rank GitHub issues
that match a developer's skills and experience level.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.tools.github_tool import search_github_issues

ISSUE_AGENT_INSTRUCTION = """You are an expert at finding the perfect open source issues for developers.

Given a list of repositories, languages, and the developer's experience level,
find beginner-friendly issues that the developer can realistically tackle.

Search strategy:
1. Search each repository for issues with labels: 'good first issue', 'help wanted', 'beginner friendly', 'documentation', 'bug'.
2. For beginners, prioritize documentation and simple bug fixes.
3. For intermediate developers, include feature requests and moderate bugs.

Ranking factors:
- **Skill match**: Issues in languages the developer knows rank higher.
- **Recency**: Newer issues are preferred (less likely to be stale).
- **Activity**: Issues with some comments (but not too many) indicate active discussion.
- **Difficulty**: Estimate easy / medium / hard based on the issue body and labels.

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

issue_agent = Agent(
    name="issue_discoverer",
    model="gemini-2.5-pro",
    instruction=ISSUE_AGENT_INSTRUCTION,
    tools=[
        FunctionTool(search_github_issues),
    ],
)

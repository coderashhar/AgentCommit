"""Profile Analyzer Agent — analyzes a developer's GitHub profile.

Uses Google ADK with Gemini 2.5 Pro to extract skills, experience level,
and areas of interest from a user's GitHub profile and repositories.
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

profile_agent = Agent(
    name="profile_analyzer",
    model="gemini-2.5-flash",
    instruction=PROFILE_AGENT_INSTRUCTION,
    tools=[
        FunctionTool(fetch_github_profile),
        FunctionTool(fetch_user_repos),
        FunctionTool(fetch_repo_languages),
    ],
)

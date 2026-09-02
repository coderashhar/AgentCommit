"""GitHub MCP toolset factory for AgentCommit agents.

Replaces the manual mcp.ClientSession scaffolding with ADK's native MCPToolset,
which plugs directly into an Agent's `tools=[]` list and has its lifecycle
(stdio process spawn, session init, cleanup) managed by the ADK runner.

Usage inside an agent factory::

    from app.mcp import build_github_mcp_toolset

    def build_planner_agent(github_token: str) -> Agent:
        mcp_toolset = build_github_mcp_toolset(
            github_token,
            tool_filter=["get_file_contents", "search_code"],
        )
        return Agent(
            model="gemini-2.5-flash",
            name="planner_agent",
            tools=[...rest_tools..., mcp_toolset],
            ...
        )

Design decisions:
- The user's OAuth token is used (not the static settings.github_mcp_token) so
  that MCP operates under the user's own GitHub permissions and rate limits.
- tool_filter limits which MCP tools the agent can call, reducing attack surface
  and prompt context.
- MCPToolset is constructed lazily (per request) because it holds the token in
  the subprocess environment. Sharing one instance across requests would mix tokens.
"""

from __future__ import annotations

import logging
from typing import Optional

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool import StdioConnectionParams
from mcp import StdioServerParameters

logger = logging.getLogger(__name__)


def build_github_mcp_toolset(
    github_token: str,
    tool_filter: Optional[list[str]] = None,
) -> MCPToolset:
    """Build an ADK MCPToolset for the GitHub MCP server bound to a request's token.

    Args:
        github_token: The user's GitHub OAuth access token. Passed as the
            GITHUB_PERSONAL_ACCESS_TOKEN environment variable to the MCP server
            subprocess, so it never appears in agent prompt text.
        tool_filter: Optional list of MCP tool names to expose to the agent.
            When None, all GitHub MCP tools are available. Prefer an explicit
            filter to limit context and surface area.

    Returns:
        An MCPToolset ready to be placed in an Agent's `tools` list.
    """
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": github_token},
    )
    connection_params = StdioConnectionParams(server_params=server_params)

    return MCPToolset(
        connection_params=connection_params,
        tool_filter=tool_filter,
    )

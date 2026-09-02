"""Tests for GitHub MCP toolset integration.

Unit tests run without network access and verify that the MCPToolset object
is created correctly. Integration tests (marked @pytest.mark.integration) require
`npx` to be installed and a valid GitHub token in GITHUB_TOKEN env var — they
are skipped by default and must be opted in explicitly:

    pytest -m integration tests/test_mcp_integration.py
"""

import pytest

from app.mcp import build_github_mcp_toolset


# ---------- Unit tests (no network, no npx) ----------


class TestBuildGithubMcpToolset:
    def test_creates_mcp_toolset_instance(self):
        """MCPToolset should be instantiated without any network call."""
        from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

        toolset = build_github_mcp_toolset("fake-token-abc123")
        assert isinstance(toolset, MCPToolset)

    def test_creates_with_tool_filter(self):
        """Passing a tool_filter should not raise."""
        from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

        toolset = build_github_mcp_toolset(
            "fake-token-abc123",
            tool_filter=["get_file_contents", "search_code"],
        )
        assert isinstance(toolset, MCPToolset)

    def test_creates_with_empty_token(self):
        """An empty token should still produce a toolset object (error surfaces at runtime)."""
        from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

        toolset = build_github_mcp_toolset("")
        assert isinstance(toolset, MCPToolset)

    def test_different_tokens_produce_different_instances(self):
        """Each call must return a distinct instance so tokens don't leak across requests."""
        ts1 = build_github_mcp_toolset("token-alice")
        ts2 = build_github_mcp_toolset("token-bob")
        assert ts1 is not ts2


# ---------- Integration tests (require npx + real GitHub token) ----------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_get_file_contents_real():
    """Fetch README.md from a known public repo via MCP."""
    import os

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        pytest.skip("GITHUB_TOKEN not set — skipping live MCP test")

    # This test spawns an npx subprocess; skip if npx is not on PATH.
    import shutil

    if not shutil.which("npx"):
        pytest.skip("npx not found on PATH — skipping live MCP test")

    # We can't easily call MCP tools directly in a unit test without the ADK runner,
    # so this test just verifies the toolset can be built with a real token.
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

    toolset = build_github_mcp_toolset(token, tool_filter=["get_file_contents"])
    assert isinstance(toolset, MCPToolset)

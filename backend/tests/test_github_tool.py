"""Tests for app.tools.github_tool — request construction and error shaping.

These cover the wiring rather than the pure logic: which query parameters actually
reach GitHub, and what callers get back when GitHub rejects the request. That is the
layer where a wrong parameter name or a dropped filter is invisible to unit tests of
the ranking modules but changes what every user sees.
"""

import httpx
import pytest

from app.tools import github_tool
from app.tools.github_tool import (
    fetch_issue_details,
    fetch_repo,
    search_github_issues,
    search_github_repos,
)


class FakeResponse:
    def __init__(self, json_data, status_code=200, text=""):
        self._json = json_data
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"status {self.status_code}",
                request=httpx.Request("GET", "https://api.github.com"),
                response=httpx.Response(self.status_code, text=self.text),
            )


@pytest.fixture
def capture(monkeypatch):
    """Patch httpx.AsyncClient and record the outgoing request."""
    calls: list[dict] = []
    box = {"response": FakeResponse([])}

    class RecordingClient:
        def __init__(self, *args, **kwargs):
            calls.append({"client_kwargs": kwargs})

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, params=None, headers=None):
            calls[-1].update({"url": url, "params": params or {}, "headers": headers or {}})
            return box["response"]

    monkeypatch.setattr(github_tool.httpx, "AsyncClient", RecordingClient)
    return {"calls": calls, "box": box}


# ---------- search_github_repos ----------


class TestSearchGithubRepos:
    @pytest.mark.asyncio
    async def test_default_sends_no_sort(self, capture):
        """The default must rank by relevance — star-sorting is what surfaced mega-repos."""
        capture["box"]["response"] = FakeResponse({"items": []})
        await search_github_repos("language:python", "tok")

        params = capture["calls"][-1]["params"]
        assert "sort" not in params
        assert "order" not in params

    @pytest.mark.asyncio
    async def test_unrecognised_sort_is_dropped(self, capture):
        capture["box"]["response"] = FakeResponse({"items": []})
        await search_github_repos("q", "tok", sort="bogus")

        assert "sort" not in capture["calls"][-1]["params"]

    @pytest.mark.asyncio
    async def test_allowlisted_sort_is_sent_with_order(self, capture):
        capture["box"]["response"] = FakeResponse({"items": []})
        await search_github_repos("q", "tok", sort="help-wanted-issues")

        params = capture["calls"][-1]["params"]
        assert params["sort"] == "help-wanted-issues"
        assert params["order"] == "desc"

    @pytest.mark.asyncio
    async def test_invalid_order_falls_back_to_desc(self, capture):
        capture["box"]["response"] = FakeResponse({"items": []})
        await search_github_repos("q", "tok", sort="updated", order="sideways")

        assert capture["calls"][-1]["params"]["order"] == "desc"

    @pytest.mark.asyncio
    async def test_order_not_sent_without_sort(self, capture):
        capture["box"]["response"] = FakeResponse({"items": []})
        await search_github_repos("q", "tok", order="asc")

        assert "order" not in capture["calls"][-1]["params"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "given,expected", [(0, 1), (-5, 1), (25, 25), (100, 100), (500, 100)]
    )
    async def test_per_page_clamped(self, capture, given, expected):
        capture["box"]["response"] = FakeResponse({"items": []})
        await search_github_repos("q", "tok", per_page=given)

        assert capture["calls"][-1]["params"]["per_page"] == expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize("given,expected", [(0, 1), (1, 1), (10, 10), (99, 10)])
    async def test_page_clamped(self, capture, given, expected):
        """GitHub search caps at 1000 results; paging past page 10 only errors."""
        capture["box"]["response"] = FakeResponse({"items": []})
        await search_github_repos("q", "tok", page=given)

        assert capture["calls"][-1]["params"]["page"] == expected

    @pytest.mark.asyncio
    async def test_returns_items(self, capture):
        capture["box"]["response"] = FakeResponse({"items": [{"full_name": "a/b"}]})
        result = await search_github_repos("q", "tok")

        assert result == [{"full_name": "a/b"}]

    @pytest.mark.asyncio
    async def test_missing_items_key_returns_empty(self, capture):
        capture["box"]["response"] = FakeResponse({})
        assert await search_github_repos("q", "tok") == []

    @pytest.mark.asyncio
    async def test_http_error_returns_error_entry(self, capture):
        capture["box"]["response"] = FakeResponse(None, status_code=422, text="bad query")
        result = await search_github_repos("q", "tok")

        assert len(result) == 1
        assert "422" in result[0]["error"]

    @pytest.mark.asyncio
    async def test_sends_bearer_token(self, capture):
        capture["box"]["response"] = FakeResponse({"items": []})
        await search_github_repos("q", "secret-token")

        assert capture["calls"][-1]["headers"]["Authorization"] == "Bearer secret-token"

    @pytest.mark.asyncio
    async def test_query_passed_through_verbatim(self, capture):
        capture["box"]["response"] = FakeResponse({"items": []})
        query = "language:Elixir stars:500..20000 good-first-issues:>3"
        await search_github_repos(query, "tok")

        assert capture["calls"][-1]["params"]["q"] == query


# ---------- search_github_issues ----------


class TestSearchGithubIssues:
    @pytest.mark.asyncio
    async def test_defaults_to_unassigned(self, capture):
        """Assigned issues are already claimed and must not be recommended."""
        capture["box"]["response"] = FakeResponse([])
        await search_github_issues("acme/widget", "tok")

        assert capture["calls"][-1]["params"]["assignee"] == "none"

    @pytest.mark.asyncio
    async def test_defaults_to_sort_updated(self, capture):
        """'updated' surfaces live maintainer attention; 'created' surfaces the unread."""
        capture["box"]["response"] = FakeResponse([])
        await search_github_issues("acme/widget", "tok")

        assert capture["calls"][-1]["params"]["sort"] == "updated"

    @pytest.mark.asyncio
    async def test_since_omitted_when_empty(self, capture):
        capture["box"]["response"] = FakeResponse([])
        await search_github_issues("acme/widget", "tok")

        assert "since" not in capture["calls"][-1]["params"]

    @pytest.mark.asyncio
    async def test_since_included_when_set(self, capture):
        capture["box"]["response"] = FakeResponse([])
        await search_github_issues("acme/widget", "tok", since="2026-06-01T00:00:00Z")

        assert capture["calls"][-1]["params"]["since"] == "2026-06-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_targets_repo_issues_endpoint(self, capture):
        capture["box"]["response"] = FakeResponse([])
        await search_github_issues("acme/widget", "tok")

        assert capture["calls"][-1]["url"].endswith("/repos/acme/widget/issues")

    @pytest.mark.asyncio
    async def test_http_error_returns_error_entry(self, capture):
        capture["box"]["response"] = FakeResponse(None, status_code=404, text="nope")
        result = await search_github_issues("acme/missing", "tok")

        assert "404" in result[0]["error"]


# ---------- fetch_repo / fetch_issue_details ----------


class TestFetchHelpers:
    @pytest.mark.asyncio
    async def test_fetch_repo_url(self, capture):
        capture["box"]["response"] = FakeResponse({"full_name": "acme/widget"})
        result = await fetch_repo("acme", "widget", "tok")

        assert capture["calls"][-1]["url"].endswith("/repos/acme/widget")
        assert result["full_name"] == "acme/widget"

    @pytest.mark.asyncio
    async def test_fetch_repo_404_returns_error_dict(self, capture):
        """A 404 is how a hallucinated repository is detected during verification."""
        capture["box"]["response"] = FakeResponse(None, status_code=404, text="Not Found")
        result = await fetch_repo("acme", "does-not-exist", "tok")

        assert "error" in result
        assert "404" in result["error"]

    @pytest.mark.asyncio
    async def test_fetch_issue_details_url(self, capture):
        capture["box"]["response"] = FakeResponse({"number": 7})
        result = await fetch_issue_details("acme", "widget", 7, "tok")

        assert capture["calls"][-1]["url"].endswith("/repos/acme/widget/issues/7")
        assert result["number"] == 7

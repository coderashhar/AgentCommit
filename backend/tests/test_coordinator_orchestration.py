"""Tests for coordinator orchestration — cache, verification, and fallback branches.

`run_repo_recommendation` and `run_issue_discovery` pick between three outcomes
(`agent`, `hybrid`, `deterministic`) depending on how much of the model's output
survives verification. Those branches decide what every user sees and none of them
were covered: the ranking modules are tested in isolation, so a wiring mistake
between them and the agent path is invisible until it reaches a browser.
"""

import pytest

from app.agents import coordinator
from app.models.schemas import (
    DiscoveredIssue,
    IssueDiscoveryResponse,
    RecommendedRepo,
    RepoRecommendationResponse,
)


def make_repo(full_name="acme/widget", stars=3000, **overrides):
    """A GitHub API repo payload inside the beginner band."""
    payload = {
        "full_name": full_name,
        "stargazers_count": stars,
        "forks_count": 200,
        "language": "Python",
        "topics": ["cli"],
        "open_issues_count": 40,
        "html_url": f"https://github.com/{full_name}",
        "pushed_at": "2026-08-30T00:00:00Z",
        "archived": False,
        "disabled": False,
        "has_issues": True,
        "fork": False,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def no_cache(monkeypatch):
    """Neutralise Redis so tests exercise the live path, and record writes."""
    writes: list[tuple[str, dict]] = []

    async def fake_get(key):
        return None

    async def fake_set(key, value, ttl_seconds=None):
        writes.append((key, value))

    monkeypatch.setattr(coordinator, "cache_get", fake_get)
    monkeypatch.setattr(coordinator, "cache_set", fake_set)
    return writes


@pytest.fixture
def agent_fails(monkeypatch):
    """Force the LLM path to raise, so the deterministic fallback runs."""

    async def boom(*args, **kwargs):
        raise RuntimeError("gemini unavailable")

    monkeypatch.setattr(coordinator, "_run_agent", boom)


# ---------- run_repo_recommendation ----------


class TestRunRepoRecommendation:
    @pytest.mark.asyncio
    async def test_cache_hit_short_circuits(self, monkeypatch):
        """A cached response must not touch the agent or GitHub at all."""
        cached = RepoRecommendationResponse(
            repositories=[RecommendedRepo(full_name="acme/cached")], source="agent"
        ).model_dump()

        async def fake_get(key):
            return cached

        called = []
        monkeypatch.setattr(coordinator, "cache_get", fake_get)
        monkeypatch.setattr(
            coordinator, "_run_agent", lambda *a, **k: called.append(1)
        )

        result = await coordinator.run_repo_recommendation(
            ["Python"], [], "beginner", [], "tok"
        )

        assert result.repositories[0].full_name == "acme/cached"
        assert not called

    @pytest.mark.asyncio
    async def test_agent_failure_falls_back_to_deterministic(
        self, monkeypatch, no_cache, agent_fails
    ):
        async def fake_search(query, token, sort="", per_page=25):
            return [make_repo()]

        monkeypatch.setattr(coordinator, "search_github_repos", fake_search)

        result = await coordinator.run_repo_recommendation(
            ["Python"], [], "beginner", [], "tok"
        )

        assert result.source == "deterministic"
        assert result.repositories

    @pytest.mark.asyncio
    async def test_empty_agent_result_falls_back(self, monkeypatch, no_cache):
        """Valid JSON with zero repositories must not be served as an empty dashboard."""

        async def empty_agent(*args, **kwargs):
            return '{"repositories": []}'

        async def fake_search(query, token, sort="", per_page=25):
            return [make_repo()]

        monkeypatch.setattr(coordinator, "_run_agent", empty_agent)
        monkeypatch.setattr(coordinator, "search_github_repos", fake_search)

        result = await coordinator.run_repo_recommendation(
            ["Python"], [], "beginner", [], "tok"
        )

        assert result.source == "deterministic"
        assert result.repositories

    @pytest.mark.asyncio
    async def test_empty_result_is_never_cached(self, monkeypatch, no_cache, agent_fails):
        """One bad run must not poison every user sharing that skill profile."""

        async def no_results(query, token, sort="", per_page=25):
            return []

        monkeypatch.setattr(coordinator, "search_github_repos", no_results)

        result = await coordinator.run_repo_recommendation(
            ["Python"], [], "beginner", [], "tok"
        )

        assert result.repositories == []
        assert no_cache == [], "an empty result must not be written to the cache"

    @pytest.mark.asyncio
    async def test_non_empty_result_is_cached(self, monkeypatch, no_cache, agent_fails):
        async def fake_search(query, token, sort="", per_page=25):
            return [make_repo()]

        monkeypatch.setattr(coordinator, "search_github_repos", fake_search)

        await coordinator.run_repo_recommendation(["Python"], [], "beginner", [], "tok")

        assert len(no_cache) == 1

    @pytest.mark.asyncio
    async def test_cache_key_includes_frameworks_and_domains(
        self, monkeypatch, no_cache, agent_fails
    ):
        """Two developers with the same languages but different stacks must not collide."""

        async def fake_search(query, token, sort="", per_page=25):
            return [make_repo()]

        monkeypatch.setattr(coordinator, "search_github_repos", fake_search)

        await coordinator.run_repo_recommendation(
            ["Python"], ["django"], "beginner", ["web"], "tok"
        )
        await coordinator.run_repo_recommendation(
            ["Python"], ["numpy"], "beginner", ["ml"], "tok"
        )

        assert no_cache[0][0] != no_cache[1][0]

    @pytest.mark.asyncio
    async def test_tier_affects_results(self, monkeypatch, no_cache, agent_fails):
        """A 150k-star repo is acceptable for advanced and rejected for beginner."""
        queries: list[str] = []

        async def fake_search(query, token, sort="", per_page=25):
            queries.append(query)
            return [make_repo(full_name="big/repo", stars=150_000)]

        monkeypatch.setattr(coordinator, "search_github_repos", fake_search)

        beginner = await coordinator.run_repo_recommendation(
            ["Python"], [], "beginner", [], "tok"
        )
        advanced = await coordinator.run_repo_recommendation(
            ["Python"], [], "advanced", [], "tok"
        )

        assert [r.full_name for r in beginner.repositories] == []
        assert [r.full_name for r in advanced.repositories] == ["big/repo"]


# ---------- _verify_recommended_repos ----------


class TestVerifyRecommendedRepos:
    @pytest.mark.asyncio
    async def test_drops_hallucinated_repo(self, monkeypatch):
        """A repository the model invented returns 404 and must be dropped."""

        async def fake_fetch(owner, repo, token):
            return {"error": "GitHub API failed with status 404"}

        monkeypatch.setattr(coordinator, "fetch_repo", fake_fetch)

        verified = await coordinator._verify_recommended_repos(
            [RecommendedRepo(full_name="acme/invented", stars=42_000)],
            coordinator.ExperienceTier.BEGINNER,
            ["Python"], [], [], "tok",
        )

        assert verified == []

    @pytest.mark.asyncio
    async def test_drops_repo_above_reject_ceiling(self, monkeypatch):
        """Even if the model insists, a mega-repo must not reach a beginner."""

        async def fake_fetch(owner, repo, token):
            return make_repo(full_name="microsoft/vscode", stars=170_000)

        monkeypatch.setattr(coordinator, "fetch_repo", fake_fetch)

        verified = await coordinator._verify_recommended_repos(
            [RecommendedRepo(full_name="microsoft/vscode")],
            coordinator.ExperienceTier.BEGINNER,
            ["TypeScript"], [], [], "tok",
        )

        assert verified == []

    @pytest.mark.asyncio
    async def test_rebuilds_fields_from_github_not_the_model(self, monkeypatch):
        """The model's numbers are discarded; GitHub's payload is the source of truth."""

        async def fake_fetch(owner, repo, token):
            return make_repo(full_name="acme/widget", stars=3000)

        monkeypatch.setattr(coordinator, "fetch_repo", fake_fetch)

        verified = await coordinator._verify_recommended_repos(
            [RecommendedRepo(full_name="acme/widget", stars=999_999, language="COBOL")],
            coordinator.ExperienceTier.BEGINNER,
            ["Python"], [], [], "tok",
        )

        assert len(verified) == 1
        assert verified[0].stars == 3000
        assert verified[0].language == "Python"

    @pytest.mark.asyncio
    async def test_deduplicates_case_insensitively(self, monkeypatch):
        calls: list[str] = []

        async def fake_fetch(owner, repo, token):
            calls.append(f"{owner}/{repo}")
            return make_repo(full_name=f"{owner}/{repo}")

        monkeypatch.setattr(coordinator, "fetch_repo", fake_fetch)

        await coordinator._verify_recommended_repos(
            [
                RecommendedRepo(full_name="acme/widget"),
                RecommendedRepo(full_name="ACME/Widget"),
            ],
            coordinator.ExperienceTier.BEGINNER,
            ["Python"], [], [], "tok",
        )

        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_malformed_full_name_dropped(self, monkeypatch):
        async def fake_fetch(owner, repo, token):
            raise AssertionError("should not fetch a malformed name")

        monkeypatch.setattr(coordinator, "fetch_repo", fake_fetch)

        verified = await coordinator._verify_recommended_repos(
            [RecommendedRepo(full_name="no-slash-here")],
            coordinator.ExperienceTier.BEGINNER,
            ["Python"], [], [], "tok",
        )

        assert verified == []


# ---------- run_issue_discovery ----------


class TestRunIssueDiscovery:
    @pytest.mark.asyncio
    async def test_agent_failure_falls_back_to_deterministic(
        self, monkeypatch, no_cache, agent_fails
    ):
        async def fake_issues(repo_full_name, github_token, labels="", **kwargs):
            return [
                {
                    "number": 1,
                    "title": "Fix a typo",
                    "html_url": "https://example.test/1",
                    "labels": [{"name": "good first issue"}],
                    "comments": 2,
                    "body": "A small fix",
                    "created_at": "2026-08-20T00:00:00Z",
                    "updated_at": "2026-08-30T00:00:00Z",
                    "assignee": None,
                    "state": "open",
                }
            ]

        async def fake_repo(owner, repo, token):
            return make_repo()

        monkeypatch.setattr(coordinator, "search_github_issues", fake_issues)
        monkeypatch.setattr(coordinator, "fetch_repo", fake_repo)

        result = await coordinator.run_issue_discovery(
            ["acme/widget"], ["Python"], "beginner", "tok"
        )

        assert result.source == "deterministic"
        assert result.issues

    @pytest.mark.asyncio
    async def test_language_lookup_bounded_by_repos_with_issues(
        self, monkeypatch, no_cache, agent_fails
    ):
        """Language lookups must not scale with the request's repository list.

        `_search_tier_issues` caps itself at ISSUE_SOURCE_REPO_LIMIT, but the language
        lookup beside it used to receive the raw request field — so a caller could
        make the backend issue one `fetch_repo` call per repository named, for repos
        that produced no issues and whose language nothing would consult.
        """
        async def fake_issues(repo_full_name, github_token, labels="", **kwargs):
            # Only one repository in the request actually has issues.
            if repo_full_name != "acme/widget":
                return []
            return [
                {
                    "number": 1,
                    "title": "Fix a typo",
                    "html_url": "https://example.test/1",
                    "labels": [{"name": "good first issue"}],
                    "comments": 2,
                    "body": "A small fix",
                    "created_at": "2026-08-20T00:00:00Z",
                    "updated_at": "2026-08-30T00:00:00Z",
                    "assignee": None,
                    "state": "open",
                }
            ]

        fetched: list[str] = []

        async def fake_repo(owner, repo, token):
            fetched.append(f"{owner}/{repo}")
            return make_repo(full_name=f"{owner}/{repo}")

        monkeypatch.setattr(coordinator, "search_github_issues", fake_issues)
        monkeypatch.setattr(coordinator, "fetch_repo", fake_repo)

        many_repos = ["acme/widget"] + [f"acme/empty-{i}" for i in range(30)]
        result = await coordinator.run_issue_discovery(
            many_repos, ["Python"], "beginner", "tok"
        )

        assert result.issues
        # Every repo fetched must be one that returned an issue.
        assert set(fetched) <= {"acme/widget"}

    @pytest.mark.asyncio
    async def test_empty_issue_result_not_cached(self, monkeypatch, no_cache, agent_fails):
        async def no_issues(repo_full_name, github_token, labels="", **kwargs):
            return []

        async def fake_repo(owner, repo, token):
            return make_repo()

        monkeypatch.setattr(coordinator, "search_github_issues", no_issues)
        monkeypatch.setattr(coordinator, "fetch_repo", fake_repo)

        result = await coordinator.run_issue_discovery(
            ["acme/widget"], ["Python"], "beginner", "tok"
        )

        assert result.issues == []
        assert no_cache == []

    @pytest.mark.asyncio
    async def test_cache_key_uses_full_repo_list(self, monkeypatch, no_cache, agent_fails):
        """Truncating the key to the first few repos made distinct requests collide."""

        async def fake_issues(repo_full_name, github_token, labels="", **kwargs):
            return []

        async def fake_repo(owner, repo, token):
            return make_repo()

        monkeypatch.setattr(coordinator, "search_github_issues", fake_issues)
        monkeypatch.setattr(coordinator, "fetch_repo", fake_repo)

        keys = []
        original = coordinator.build_cache_key
        monkeypatch.setattr(
            coordinator,
            "build_cache_key",
            lambda *a, **k: keys.append(original(*a, **k)) or keys[-1],
        )

        four = ["a/1", "a/2", "a/3", "a/4"]
        await coordinator.run_issue_discovery(four, ["Python"], "beginner", "tok")
        await coordinator.run_issue_discovery(four[:3] + ["a/5"], ["Python"], "beginner", "tok")

        assert keys[0] != keys[1]

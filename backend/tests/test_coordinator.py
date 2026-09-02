"""Tests for coordinator helper functions — JSON parsing, deduplication, inference."""

import pytest

from app.agents import coordinator
from app.tools.repo_ranking import ExperienceTier
from app.agents.coordinator import (
    _parse_json_response,
    _ordered_unique,
    _fallback_experience_level,
    _infer_keywords,
    FRAMEWORK_KEYWORDS,
    DOMAIN_KEYWORDS,
)


# ---------- _parse_json_response ----------


class TestParseJsonResponse:
    def test_clean_json(self):
        result = _parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_markdown_wrapped_json(self):
        text = '```json\n{"key": "value"}\n```'
        result = _parse_json_response(text)
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        text = 'Here is the result: {"key": "value"} hope that helps!'
        result = _parse_json_response(text)
        assert result == {"key": "value"}

    def test_empty_response_raises(self):
        with pytest.raises(RuntimeError, match="empty"):
            _parse_json_response("")

    def test_whitespace_only_raises(self):
        with pytest.raises(RuntimeError, match="empty"):
            _parse_json_response("   \n  ")

    def test_invalid_json_raises(self):
        with pytest.raises(RuntimeError, match="valid JSON"):
            _parse_json_response("not json at all")

    def test_nested_json(self):
        text = '{"repos": [{"name": "a"}, {"name": "b"}]}'
        result = _parse_json_response(text)
        assert len(result["repos"]) == 2


# ---------- _ordered_unique ----------


class TestOrderedUnique:
    def test_preserves_order(self):
        result = _ordered_unique(["Python", "JavaScript", "Python", "Rust"])
        assert result == ["Python", "JavaScript", "Rust"]

    def test_case_insensitive_dedup(self):
        result = _ordered_unique(["python", "Python", "PYTHON"])
        assert result == ["python"]

    def test_strips_whitespace(self):
        result = _ordered_unique(["  Python  ", "python"])
        assert result == ["Python"]

    def test_drops_empty_strings(self):
        result = _ordered_unique(["Python", "", "  ", "Rust"])
        assert result == ["Python", "Rust"]

    def test_empty_input(self):
        assert _ordered_unique([]) == []


# ---------- _fallback_experience_level ----------


class TestFallbackExperienceLevel:
    def test_beginner_few_repos(self):
        repos = [{"stargazers_count": 2, "language": "Python"}] * 3
        assert _fallback_experience_level(repos) == "beginner"

    def test_intermediate_moderate_repos(self):
        repos = [{"stargazers_count": 3, "language": "Python"}] * 8
        assert _fallback_experience_level(repos) == "intermediate"

    def test_advanced_many_repos(self):
        repos = [{"stargazers_count": 5, "language": "Python"}] * 25
        assert _fallback_experience_level(repos) == "advanced"

    def test_advanced_high_stars(self):
        repos = [{"stargazers_count": 50, "language": "Python"}] * 3
        assert _fallback_experience_level(repos) == "advanced"

    def test_advanced_many_languages(self):
        languages = ["Python", "JavaScript", "Rust", "Go", "TypeScript"]
        repos = [{"stargazers_count": 1, "language": lang} for lang in languages]
        assert _fallback_experience_level(repos) == "advanced"

    def test_empty_repos_beginner(self):
        assert _fallback_experience_level([]) == "beginner"


# ---------- _infer_keywords ----------


class TestInferKeywords:
    def test_framework_from_repo_name(self):
        repos = [{"name": "my-react-app", "description": "", "topics": []}]
        result = _infer_keywords(repos, FRAMEWORK_KEYWORDS)
        assert "React" in result

    def test_framework_from_topics(self):
        repos = [{"name": "project", "description": "", "topics": ["django", "python"]}]
        result = _infer_keywords(repos, FRAMEWORK_KEYWORDS)
        assert "Django" in result

    def test_framework_from_description(self):
        repos = [{"name": "proj", "description": "Built with FastAPI and Redis", "topics": []}]
        result = _infer_keywords(repos, FRAMEWORK_KEYWORDS)
        assert "FastAPI" in result

    def test_domain_inference(self):
        repos = [{"name": "ml-pipeline", "description": "Machine learning tools", "topics": ["ml"]}]
        result = _infer_keywords(repos, DOMAIN_KEYWORDS)
        assert "machine learning" in result

    def test_deduplication(self):
        repos = [
            {"name": "react-app", "description": "A react project", "topics": ["react"]},
        ]
        result = _infer_keywords(repos, FRAMEWORK_KEYWORDS)
        assert result.count("React") == 1

    def test_no_matches(self):
        repos = [{"name": "xyz", "description": "something", "topics": []}]
        result = _infer_keywords(repos, FRAMEWORK_KEYWORDS)
        assert result == []


# ---------- _search_tier_repos escalation ----------


class TestSearchTierReposEscalation:
    """The strict->relaxed escalation and its split labelled-issue queries.

    These exercise the real code path rather than the query builder in isolation:
    a missing IssueQualifier import once broke this while every builder unit test
    still passed.
    """

    @pytest.mark.asyncio
    async def test_escalates_to_split_queries_when_strict_is_empty(self, monkeypatch):
        seen: list[str] = []

        async def fake_search(query, token, sort="", per_page=25):
            seen.append(query)
            return []

        monkeypatch.setattr(coordinator, "search_github_repos", fake_search)
        await coordinator._search_tier_repos(
            ExperienceTier.BEGINNER, ["Elixir"], [], [], "tok"
        )

        both = [q for q in seen if "good-first-issues" in q and "help-wanted-issues" in q]
        good_first_only = [
            q for q in seen if "good-first-issues" in q and "help-wanted-issues" not in q
        ]
        help_wanted_only = [
            q for q in seen if "help-wanted-issues" in q and "good-first-issues" not in q
        ]

        assert both, "strict pass should conjoin both qualifiers"
        assert good_first_only, "relaxed pass should issue a good-first-issues-only query"
        assert help_wanted_only, "relaxed pass should issue a help-wanted-issues-only query"

    @pytest.mark.asyncio
    async def test_productive_strict_pass_does_not_escalate(self, monkeypatch):
        """A strict pass that finds anything must not spend calls on the relaxed pass."""
        seen: list[str] = []

        async def fake_search(query, token, sort="", per_page=25):
            seen.append(query)
            return [
                {
                    "full_name": "acme/widget",
                    "stargazers_count": 3000,
                    "open_issues_count": 20,
                    "html_url": "https://example.test",
                }
            ]

        monkeypatch.setattr(coordinator, "search_github_repos", fake_search)
        await coordinator._search_tier_repos(
            ExperienceTier.BEGINNER, ["Python"], [], [], "tok"
        )

        split_queries = [
            q for q in seen if "good-first-issues" in q and "help-wanted-issues" not in q
        ]
        assert not split_queries, "should not escalate after a productive strict pass"

    @pytest.mark.asyncio
    async def test_never_sorts_by_stars(self, monkeypatch):
        """Star-sorting is what surfaced mega-repos; no pass may reintroduce it."""
        sorts: list[str] = []

        async def fake_search(query, token, sort="", per_page=25):
            sorts.append(sort)
            return []

        monkeypatch.setattr(coordinator, "search_github_repos", fake_search)
        await coordinator._search_tier_repos(
            ExperienceTier.BEGINNER, ["Rust"], [], [], "tok"
        )

        assert sorts, "expected at least one search"
        assert "stars" not in sorts

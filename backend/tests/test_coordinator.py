"""Tests for coordinator helper functions — JSON parsing, deduplication, inference."""

import pytest

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

"""Shared fixtures for AgentCommit backend tests."""

from datetime import date, datetime, timezone

import pytest

from app.tools.repo_ranking import ExperienceTier


@pytest.fixture
def fixed_today() -> date:
    """A deterministic reference date for query building."""
    return date(2026, 9, 1)


@pytest.fixture
def fixed_now() -> datetime:
    """A deterministic reference datetime for scoring."""
    return datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def beginner_tier() -> ExperienceTier:
    return ExperienceTier.BEGINNER


@pytest.fixture
def intermediate_tier() -> ExperienceTier:
    return ExperienceTier.INTERMEDIATE


@pytest.fixture
def advanced_tier() -> ExperienceTier:
    return ExperienceTier.ADVANCED


@pytest.fixture
def sample_repo_payload() -> dict:
    """A realistic GitHub repository payload for a beginner-tier repo."""
    return {
        "full_name": "example/starter-project",
        "name": "starter-project",
        "description": "A beginner-friendly web framework tutorial project",
        "stargazers_count": 3500,
        "forks_count": 450,
        "open_issues_count": 42,
        "language": "Python",
        "topics": ["python", "fastapi", "web", "beginner-friendly"],
        "html_url": "https://github.com/example/starter-project",
        "pushed_at": "2026-08-30T10:00:00Z",
        "created_at": "2024-01-15T08:00:00Z",
        "archived": False,
        "disabled": False,
        "fork": False,
        "has_issues": True,
    }


@pytest.fixture
def sample_issue_payload() -> dict:
    """A realistic GitHub issue payload."""
    return {
        "title": "Fix typo in getting started guide",
        "number": 123,
        "state": "open",
        "labels": [{"name": "good first issue"}, {"name": "documentation"}],
        "html_url": "https://github.com/example/starter-project/issues/123",
        "created_at": "2026-08-25T10:00:00Z",
        "updated_at": "2026-08-28T14:00:00Z",
        "comments": 3,
        "body": "There's a typo on line 42 of the getting started guide. It says 'improt' instead of 'import'.",
        "assignee": None,
        "assignees": [],
        "locked": False,
    }

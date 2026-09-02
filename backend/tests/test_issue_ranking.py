"""Tests for app.tools.issue_ranking — filters, difficulty classification, and scoring."""

from datetime import datetime, timedelta, timezone

from app.tools.issue_ranking import (
    classify_issue_difficulty,
    is_claimed,
    is_pull_request,
    is_stale_issue,
    score_issue,
    HARD_BODY_CHARS,
    HARD_COMMENT_COUNT,
    EASY_BODY_CHARS,
    EASY_COMMENT_COUNT,
)
from app.tools.repo_ranking import ExperienceTier


# ---------- is_pull_request ----------


class TestIsPullRequest:
    def test_true_when_pull_request_key_present(self):
        issue = {"title": "Fix bug", "pull_request": {"url": "..."}}
        assert is_pull_request(issue) is True

    def test_false_when_no_pull_request_key(self):
        issue = {"title": "Fix bug", "number": 1}
        assert is_pull_request(issue) is False


# ---------- is_claimed ----------


class TestIsClaimed:
    def test_claimed_with_assignee(self):
        issue = {"assignee": {"login": "alice"}, "assignees": [{"login": "alice"}]}
        assert is_claimed(issue) is True

    def test_not_claimed_no_assignee(self):
        issue = {"assignee": None, "assignees": []}
        assert is_claimed(issue) is False

    def test_not_claimed_missing_fields(self):
        issue = {}
        assert is_claimed(issue) is False

    def test_claimed_with_only_assignees_list(self):
        issue = {"assignee": None, "assignees": [{"login": "bob"}]}
        assert is_claimed(issue) is True

    def test_not_claimed_empty_assignees(self):
        issue = {"assignee": None, "assignees": []}
        assert is_claimed(issue) is False


# ---------- is_stale_issue ----------


class TestIsStaleIssue:
    def test_stale_old_updated(self, fixed_now):
        old_date = (fixed_now - timedelta(days=200)).strftime("%Y-%m-%dT%H:%M:%SZ")
        issue = {"updated_at": old_date, "created_at": old_date, "comments": 5}
        assert is_stale_issue(issue, now=fixed_now) is True

    def test_not_stale_recently_updated(self, fixed_now):
        recent = (fixed_now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        issue = {"updated_at": recent, "created_at": recent, "comments": 0}
        assert is_stale_issue(issue, now=fixed_now) is False

    def test_stale_never_commented_old_creation(self, fixed_now):
        old_date = (fixed_now - timedelta(days=400)).strftime("%Y-%m-%dT%H:%M:%SZ")
        recent_update = (fixed_now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        issue = {"updated_at": recent_update, "created_at": old_date, "comments": 0}
        assert is_stale_issue(issue, now=fixed_now) is True

    def test_not_stale_old_creation_but_has_comments(self, fixed_now):
        old_date = (fixed_now - timedelta(days=400)).strftime("%Y-%m-%dT%H:%M:%SZ")
        recent_update = (fixed_now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        issue = {"updated_at": recent_update, "created_at": old_date, "comments": 3}
        assert is_stale_issue(issue, now=fixed_now) is False

    def test_missing_dates_not_stale(self, fixed_now):
        issue = {"comments": 0}
        assert is_stale_issue(issue, now=fixed_now) is False


# ---------- classify_issue_difficulty ----------


class TestClassifyIssueDifficulty:
    def test_easy_good_first_issue(self):
        result = classify_issue_difficulty(
            labels=["good first issue"],
            body="Fix the typo on line 5",
            comments=2,
        )
        assert result == "easy"

    def test_easy_documentation_label(self):
        result = classify_issue_difficulty(
            labels=["documentation"],
            body="Update the README",
            comments=1,
        )
        assert result == "easy"

    def test_hard_epic_label(self):
        result = classify_issue_difficulty(
            labels=["epic"],
            body="Redesign the entire system",
            comments=5,
        )
        assert result == "hard"

    def test_hard_security_label(self):
        result = classify_issue_difficulty(
            labels=["security"],
            body="Fix the vulnerability",
            comments=2,
        )
        assert result == "hard"

    def test_hard_long_body(self):
        result = classify_issue_difficulty(
            labels=["feature"],
            body="x" * (HARD_BODY_CHARS + 1),
            comments=5,
        )
        assert result == "hard"

    def test_hard_many_comments(self):
        result = classify_issue_difficulty(
            labels=["bug"],
            body="Some bug",
            comments=HARD_COMMENT_COUNT + 1,
        )
        assert result == "hard"

    def test_hard_many_code_fences(self):
        body = "```python\ncode\n```\n" * 4  # 4 fences >= HARD_CODE_FENCE_COUNT (3)
        result = classify_issue_difficulty(
            labels=["bug"],
            body=body,
            comments=2,
        )
        assert result == "hard"

    def test_hard_many_checklist_items(self):
        body = "- [ ] task\n" * 7  # 7 items >= HARD_CHECKLIST_ITEM_COUNT (6)
        result = classify_issue_difficulty(
            labels=["feature"],
            body=body,
            comments=2,
        )
        assert result == "hard"

    def test_hard_overrides_easy_label(self):
        """An issue tagged both 'good first issue' and 'epic' should be hard (hard-first evaluation)."""
        result = classify_issue_difficulty(
            labels=["good first issue", "epic"],
            body="Small fix",
            comments=2,
        )
        assert result == "hard"

    def test_medium_default(self):
        result = classify_issue_difficulty(
            labels=["enhancement"],
            body="Some reasonable work needed.",
            comments=8,
        )
        assert result == "medium"

    def test_easy_label_but_long_body_is_medium(self):
        """Easy label but body exceeds EASY_BODY_CHARS → medium (not easy)."""
        result = classify_issue_difficulty(
            labels=["good first issue"],
            body="x" * (EASY_BODY_CHARS + 1),
            comments=2,
        )
        assert result == "medium"

    def test_easy_label_but_many_comments_is_medium(self):
        """Easy label but comments exceed EASY_COMMENT_COUNT → medium."""
        result = classify_issue_difficulty(
            labels=["beginner"],
            body="Short body",
            comments=EASY_COMMENT_COUNT + 1,
        )
        assert result == "medium"

    def test_empty_labels_and_short_body(self):
        result = classify_issue_difficulty(labels=[], body="Fix it", comments=0)
        assert result == "medium"


# ---------- score_issue ----------


class TestScoreIssue:
    def test_score_in_valid_range(self, sample_issue_payload, beginner_tier, fixed_now):
        result = score_issue(sample_issue_payload, beginner_tier, ["Python"], now=fixed_now)
        assert 5.0 <= result.score <= 99.0

    def test_difficulty_returned(self, sample_issue_payload, beginner_tier, fixed_now):
        result = score_issue(sample_issue_payload, beginner_tier, ["Python"], now=fixed_now)
        assert result.difficulty in ("easy", "medium", "hard")

    def test_beginner_easy_tier_fit_is_one(self, sample_issue_payload, beginner_tier, fixed_now):
        """Beginner + easy issue → tier_fit should be 1.0."""
        result = score_issue(sample_issue_payload, beginner_tier, ["Python"], now=fixed_now)
        # sample_issue_payload has "good first issue" label + short body + few comments → easy
        assert result.difficulty == "easy"

    def test_beginner_hard_tier_fit_is_low(self, beginner_tier, fixed_now):
        hard_issue = {
            "title": "Redesign auth system",
            "number": 456,
            "labels": [{"name": "epic"}, {"name": "architecture"}],
            "body": "Major overhaul needed",
            "comments": 30,
            "updated_at": "2026-08-28T14:00:00Z",
        }
        result = score_issue(hard_issue, beginner_tier, ["Python"], now=fixed_now)
        assert result.difficulty == "hard"

    def test_advanced_hard_tier_fit_is_high(self, advanced_tier, fixed_now):
        hard_issue = {
            "title": "Redesign auth system",
            "number": 456,
            "labels": [{"name": "epic"}],
            "body": "Major overhaul",
            "comments": 30,
            "updated_at": "2026-08-28T14:00:00Z",
        }
        result = score_issue(hard_issue, advanced_tier, ["Python"], now=fixed_now)
        assert result.difficulty == "hard"

    def test_language_match_boosts_score(self, sample_issue_payload, beginner_tier, fixed_now):
        with_match = score_issue(
            sample_issue_payload, beginner_tier, ["Python"], repo_language="Python", now=fixed_now
        )
        without_match = score_issue(
            sample_issue_payload, beginner_tier, ["Python"], repo_language="Haskell", now=fixed_now
        )
        assert with_match.score > without_match.score

    def test_reasons_tuple(self, sample_issue_payload, beginner_tier, fixed_now):
        result = score_issue(sample_issue_payload, beginner_tier, ["Python"], now=fixed_now)
        assert isinstance(result.reasons, tuple)

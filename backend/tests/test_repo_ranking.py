"""Tests for app.tools.repo_ranking — query builder, rejection, and scoring."""

from datetime import date, datetime, timedelta, timezone

from app.tools.repo_ranking import (
    ExperienceTier,
    IssueQualifier,
    TIER_BANDS,
    build_repo_query,
    format_match_reason,
    repo_is_rejected,
    score_repo,
)


# ---------- ExperienceTier.from_experience_level ----------


class TestExperienceTierFromLevel:
    def test_beginner(self):
        assert ExperienceTier.from_experience_level("beginner") is ExperienceTier.BEGINNER

    def test_intermediate(self):
        assert ExperienceTier.from_experience_level("intermediate") is ExperienceTier.INTERMEDIATE

    def test_advanced(self):
        assert ExperienceTier.from_experience_level("advanced") is ExperienceTier.ADVANCED

    def test_unknown_falls_back_to_beginner(self):
        assert ExperienceTier.from_experience_level("expert") is ExperienceTier.BEGINNER

    def test_empty_falls_back_to_beginner(self):
        assert ExperienceTier.from_experience_level("") is ExperienceTier.BEGINNER

    def test_none_falls_back_to_beginner(self):
        assert ExperienceTier.from_experience_level(None) is ExperienceTier.BEGINNER

    def test_case_insensitive(self):
        assert ExperienceTier.from_experience_level("ADVANCED") is ExperienceTier.ADVANCED

    def test_whitespace_stripped(self):
        assert ExperienceTier.from_experience_level("  intermediate  ") is ExperienceTier.INTERMEDIATE


# ---------- build_repo_query ----------


class TestBuildRepoQuery:
    def test_beginner_star_bounds(self, fixed_today):
        query = build_repo_query(ExperienceTier.BEGINNER, today=fixed_today)
        assert "stars:500..20000" in query

    def test_beginner_good_first_issues(self, fixed_today):
        query = build_repo_query(ExperienceTier.BEGINNER, today=fixed_today)
        assert "good-first-issues:>3" in query

    def test_beginner_archived_false(self, fixed_today):
        query = build_repo_query(ExperienceTier.BEGINNER, today=fixed_today)
        assert "archived:false" in query

    def test_advanced_no_star_ceiling(self, fixed_today):
        query = build_repo_query(ExperienceTier.ADVANCED, today=fixed_today)
        assert "stars:>=2000" in query
        # Should NOT have a range like stars:X..Y
        assert "stars:2000.." not in query

    def test_advanced_no_good_first_issues_required(self, fixed_today):
        query = build_repo_query(ExperienceTier.ADVANCED, today=fixed_today)
        assert "good-first-issues" not in query

    def test_language_qualifier(self, fixed_today):
        query = build_repo_query(ExperienceTier.BEGINNER, language="python", today=fixed_today)
        assert "language:python" in query

    def test_topic_qualifier(self, fixed_today):
        query = build_repo_query(ExperienceTier.BEGINNER, topic="react", today=fixed_today)
        assert "topic:react" in query

    def test_pushed_within_days(self, fixed_today):
        query = build_repo_query(ExperienceTier.BEGINNER, today=fixed_today)
        expected_since = fixed_today - timedelta(days=30)
        assert f"pushed:>{expected_since.isoformat()}" in query

    def test_relaxed_keeps_star_ceiling(self, fixed_today):
        """The relaxed pass must NOT widen max_stars — that's how mega-repos get back in."""
        query = build_repo_query(ExperienceTier.BEGINNER, relaxed=True, today=fixed_today)
        assert "20000" in query

    def test_relaxed_widens_min_stars(self, fixed_today):
        query = build_repo_query(ExperienceTier.BEGINNER, relaxed=True, today=fixed_today)
        # Strict min is 500, relaxed = 500 * 0.6 = 300
        assert "stars:300.." in query

    def test_relaxed_drops_mirror_and_template(self, fixed_today):
        strict_query = build_repo_query(ExperienceTier.BEGINNER, relaxed=False, today=fixed_today)
        relaxed_query = build_repo_query(ExperienceTier.BEGINNER, relaxed=True, today=fixed_today)
        assert "mirror:false" in strict_query
        assert "mirror:false" not in relaxed_query

    def test_is_public(self, fixed_today):
        query = build_repo_query(ExperienceTier.BEGINNER, today=fixed_today)
        assert "is:public" in query


# ---------- IssueQualifier splitting ----------


class TestIssueQualifier:
    """Conjoining both labelled-issue qualifiers starves small ecosystems.

    Measured against live GitHub for Elixir at the relaxed beginner band:
    both-conjoined returns 2 repositories, good-first-issues alone returns 5,
    help-wanted-issues alone returns 11, and the union of the two is 14.
    """

    def test_both_is_the_default(self, fixed_today):
        default_query = build_repo_query(ExperienceTier.BEGINNER, today=fixed_today)
        explicit_query = build_repo_query(
            ExperienceTier.BEGINNER, issue_qualifier=IssueQualifier.BOTH, today=fixed_today
        )
        assert default_query == explicit_query

    def test_both_requires_each_qualifier(self, fixed_today):
        query = build_repo_query(
            ExperienceTier.BEGINNER, issue_qualifier=IssueQualifier.BOTH, today=fixed_today
        )
        assert "good-first-issues:>" in query
        assert "help-wanted-issues:>" in query

    def test_good_first_omits_help_wanted(self, fixed_today):
        query = build_repo_query(
            ExperienceTier.BEGINNER, issue_qualifier=IssueQualifier.GOOD_FIRST, today=fixed_today
        )
        assert "good-first-issues:>" in query
        assert "help-wanted-issues:>" not in query

    def test_help_wanted_omits_good_first(self, fixed_today):
        query = build_repo_query(
            ExperienceTier.BEGINNER, issue_qualifier=IssueQualifier.HELP_WANTED, today=fixed_today
        )
        assert "help-wanted-issues:>" in query
        assert "good-first-issues:>" not in query

    def test_split_still_keeps_star_ceiling(self, fixed_today):
        """Splitting qualifiers must not become a backdoor around the tier ceiling."""
        for qualifier in IssueQualifier:
            query = build_repo_query(
                ExperienceTier.BEGINNER,
                relaxed=True,
                issue_qualifier=qualifier,
                today=fixed_today,
            )
            assert "..20000" in query

    def test_advanced_tier_has_no_good_first_requirement(self, fixed_today):
        """Advanced omits good-first-issues entirely, so the split is a no-op there."""
        query = build_repo_query(
            ExperienceTier.ADVANCED, issue_qualifier=IssueQualifier.GOOD_FIRST, today=fixed_today
        )
        assert "good-first-issues:>" not in query


# ---------- repo_is_rejected ----------


class TestRepoIsRejected:
    def test_archived_repo_rejected(self, beginner_tier):
        repo = {"archived": True, "open_issues_count": 10, "stargazers_count": 1000}
        assert repo_is_rejected(repo, beginner_tier) is True

    def test_disabled_repo_rejected(self, beginner_tier):
        repo = {"disabled": True, "open_issues_count": 10, "stargazers_count": 1000}
        assert repo_is_rejected(repo, beginner_tier) is True

    def test_zero_issues_rejected(self, beginner_tier):
        repo = {"open_issues_count": 0, "stargazers_count": 1000}
        assert repo_is_rejected(repo, beginner_tier) is True

    def test_mega_repo_rejected_beginner(self, beginner_tier):
        """170k-star repo like microsoft/vscode must be rejected for beginners."""
        repo = {"stargazers_count": 170_000, "open_issues_count": 5000}
        assert repo_is_rejected(repo, beginner_tier) is True

    def test_mega_repo_rejected_intermediate(self, intermediate_tier):
        repo = {"stargazers_count": 170_000, "open_issues_count": 5000}
        assert repo_is_rejected(repo, intermediate_tier) is True

    def test_mega_repo_not_rejected_advanced(self, advanced_tier):
        """Advanced tier has no reject_star_ceiling."""
        repo = {"stargazers_count": 170_000, "open_issues_count": 5000}
        assert repo_is_rejected(repo, advanced_tier) is False

    def test_valid_beginner_repo_not_rejected(self, beginner_tier, sample_repo_payload):
        assert repo_is_rejected(sample_repo_payload, beginner_tier) is False

    def test_has_issues_false_rejected(self, beginner_tier):
        repo = {"has_issues": False, "open_issues_count": 10, "stargazers_count": 1000}
        assert repo_is_rejected(repo, beginner_tier) is True

    def test_has_issues_missing_not_rejected(self, beginner_tier):
        """Missing has_issues key should NOT reject."""
        repo = {"open_issues_count": 10, "stargazers_count": 1000}
        assert repo_is_rejected(repo, beginner_tier) is False

    def test_at_beginner_ceiling(self, beginner_tier):
        """Exactly at the reject ceiling (60k) should not be rejected."""
        repo = {"stargazers_count": 60_000, "open_issues_count": 100}
        assert repo_is_rejected(repo, beginner_tier) is False

    def test_just_above_beginner_ceiling(self, beginner_tier):
        repo = {"stargazers_count": 60_001, "open_issues_count": 100}
        assert repo_is_rejected(repo, beginner_tier) is True


# ---------- score_repo ----------


class TestScoreRepo:
    def test_returns_score_in_valid_range(self, sample_repo_payload, beginner_tier, fixed_now):
        result = score_repo(sample_repo_payload, beginner_tier, ["Python"], now=fixed_now)
        assert 5.0 <= result.score <= 99.0

    def test_primary_language_match(self, sample_repo_payload, beginner_tier, fixed_now):
        result = score_repo(sample_repo_payload, beginner_tier, ["Python"], now=fixed_now)
        assert result.signals["language_match"] == 1.0

    def test_secondary_language_match(self, sample_repo_payload, beginner_tier, fixed_now):
        result = score_repo(sample_repo_payload, beginner_tier, ["JavaScript", "Python"], now=fixed_now)
        assert result.signals["language_match"] == 0.85

    def test_no_language_match(self, sample_repo_payload, beginner_tier, fixed_now):
        result = score_repo(sample_repo_payload, beginner_tier, ["Rust", "Go"], now=fixed_now)
        assert result.signals["language_match"] == 0.0

    def test_empty_languages_neutral(self, sample_repo_payload, beginner_tier, fixed_now):
        result = score_repo(sample_repo_payload, beginner_tier, [], now=fixed_now)
        assert result.signals["language_match"] == 0.5

    def test_star_fit_ideal_range(self, beginner_tier, fixed_now):
        """3500 stars is within beginner ideal range (1000..8000)."""
        repo = {"stargazers_count": 3500, "open_issues_count": 50, "pushed_at": "2026-08-30T10:00:00Z"}
        result = score_repo(repo, beginner_tier, ["Python"], now=fixed_now)
        assert result.signals["star_fit"] == 1.0

    def test_fork_penalty(self, sample_repo_payload, beginner_tier, fixed_now):
        forked = {**sample_repo_payload, "fork": True}
        not_forked = {**sample_repo_payload, "fork": False}
        forked_result = score_repo(forked, beginner_tier, ["Python"], now=fixed_now)
        not_forked_result = score_repo(not_forked, beginner_tier, ["Python"], now=fixed_now)
        assert forked_result.score < not_forked_result.score

    def test_out_of_band_penalty(self, beginner_tier, fixed_now):
        """A repo outside the star band gets penalized."""
        out_of_band = {
            "stargazers_count": 100,  # below beginner min of 500
            "open_issues_count": 50,
            "pushed_at": "2026-08-30T10:00:00Z",
            "language": "Python",
        }
        in_band = {
            "stargazers_count": 3500,  # within beginner ideal
            "open_issues_count": 50,
            "pushed_at": "2026-08-30T10:00:00Z",
            "language": "Python",
        }
        out_result = score_repo(out_of_band, beginner_tier, ["Python"], now=fixed_now)
        in_result = score_repo(in_band, beginner_tier, ["Python"], now=fixed_now)
        assert out_result.score < in_result.score

    def test_recency_recent_push(self, beginner_tier, fixed_now):
        repo = {"stargazers_count": 3500, "open_issues_count": 50, "pushed_at": "2026-08-30T10:00:00Z"}
        result = score_repo(repo, beginner_tier, ["Python"], now=fixed_now)
        assert result.signals["recency"] == 1.0

    def test_recency_stale_push(self, beginner_tier, fixed_now):
        repo = {"stargazers_count": 3500, "open_issues_count": 50, "pushed_at": "2026-01-01T10:00:00Z"}
        result = score_repo(repo, beginner_tier, ["Python"], now=fixed_now)
        assert result.signals["recency"] == 0.0

    def test_recency_missing_neutral(self, beginner_tier, fixed_now):
        repo = {"stargazers_count": 3500, "open_issues_count": 50}
        result = score_repo(repo, beginner_tier, ["Python"], now=fixed_now)
        assert result.signals["recency"] == 0.5

    def test_topic_overlap_with_frameworks(self, beginner_tier, fixed_now):
        repo = {
            "stargazers_count": 3500,
            "open_issues_count": 50,
            "pushed_at": "2026-08-30T10:00:00Z",
            "language": "Python",
            "topics": ["fastapi", "web", "python"],
        }
        result = score_repo(repo, beginner_tier, ["Python"], frameworks=["FastAPI"], now=fixed_now)
        assert "topic_overlap" in result.signals
        assert result.signals["topic_overlap"] > 0.0

    def test_reasons_not_empty_for_good_match(self, sample_repo_payload, beginner_tier, fixed_now):
        result = score_repo(sample_repo_payload, beginner_tier, ["Python"], now=fixed_now)
        assert len(result.reasons) > 0


# ---------- format_match_reason ----------


class TestFormatMatchReason:
    def test_empty_reasons_fallback(self):
        result = format_match_reason([], ExperienceTier.BEGINNER)
        assert "beginner" in result.lower()

    def test_joins_reasons(self):
        reasons = ["Written in Python.", "Actively maintained."]
        result = format_match_reason(reasons, ExperienceTier.BEGINNER)
        assert "Written in Python." in result
        assert "Actively maintained." in result

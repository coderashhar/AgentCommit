"""Tests for request-schema bounds.

Every request field except the two commit/mentor text fields was unbounded, so a
single request could name an arbitrary number of repositories — each one costing
GitHub calls — or carry megabytes of string into an agent prompt. These tests pin
the outer walls; they are not business rules, and the values below are deliberately
far above anything the UI sends.
"""

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    MAX_REQUEST_REPOS,
    MAX_SKILL_ITEMS,
    CommitMessageRequest,
    GitHubAuthRequest,
    ImplementationPlanRequest,
    IssueDiscoveryRequest,
    IssueExplanationRequest,
    MentorChatRequest,
    ProfileAnalysisRequest,
    RepoRecommendationRequest,
    SaveIssueRequest,
)


class TestIssueDiscoveryBounds:
    def test_accepts_what_the_dashboard_sends(self):
        """The UI sends 10 repositories; the coordinator truncates to 12."""
        request = IssueDiscoveryRequest(
            repositories=[f"acme/repo-{i}" for i in range(10)],
            languages=["Python", "TypeScript"],
            experience_level="beginner",
        )
        assert len(request.repositories) == 10

    def test_accepts_exactly_the_cap(self):
        request = IssueDiscoveryRequest(
            repositories=[f"acme/repo-{i}" for i in range(MAX_REQUEST_REPOS)]
        )
        assert len(request.repositories) == MAX_REQUEST_REPOS

    def test_rejects_beyond_the_cap(self):
        """This is the field that multiplies GitHub calls linearly."""
        with pytest.raises(ValidationError):
            IssueDiscoveryRequest(
                repositories=[f"acme/repo-{i}" for i in range(MAX_REQUEST_REPOS + 1)]
            )

    def test_rejects_overlong_repo_name(self):
        with pytest.raises(ValidationError):
            IssueDiscoveryRequest(repositories=["a" * 200])

    def test_rejects_overlong_language_list(self):
        with pytest.raises(ValidationError):
            IssueDiscoveryRequest(
                repositories=["acme/widget"],
                languages=["Python"] * (MAX_SKILL_ITEMS + 1),
            )


class TestRepoRecommendationBounds:
    def test_accepts_a_realistic_profile(self):
        request = RepoRecommendationRequest(
            languages=["Python", "JavaScript"],
            frameworks=["Django", "React"],
            domains=["web", "cli"],
            experience_level="intermediate",
        )
        assert request.experience_level == "intermediate"

    def test_rejects_overlong_skill_lists(self):
        with pytest.raises(ValidationError):
            RepoRecommendationRequest(languages=["Python"] * (MAX_SKILL_ITEMS + 1))

    def test_rejects_overlong_single_skill(self):
        with pytest.raises(ValidationError):
            RepoRecommendationRequest(languages=["x" * 100])


class TestIdentifierBounds:
    def test_username_within_github_limit(self):
        assert ProfileAnalysisRequest(username="a" * 39).username == "a" * 39

    def test_username_beyond_github_limit_rejected(self):
        with pytest.raises(ValidationError):
            ProfileAnalysisRequest(username="a" * 40)

    def test_oauth_code_bounded(self):
        with pytest.raises(ValidationError):
            GitHubAuthRequest(code="a" * 513)

    @pytest.mark.parametrize(
        "model", [IssueExplanationRequest, ImplementationPlanRequest, MentorChatRequest]
    )
    def test_owner_and_repo_bounded(self, model):
        kwargs = {"owner": "acme", "repo": "r" * 101, "issue_number": 1}
        if model is MentorChatRequest:
            kwargs["message"] = "hi"
        with pytest.raises(ValidationError):
            model(**kwargs)

    @pytest.mark.parametrize(
        "model", [IssueExplanationRequest, ImplementationPlanRequest, MentorChatRequest]
    )
    def test_issue_number_must_be_positive(self, model):
        kwargs = {"owner": "acme", "repo": "widget", "issue_number": 0}
        if model is MentorChatRequest:
            kwargs["message"] = "hi"
        with pytest.raises(ValidationError):
            model(**kwargs)

    def test_valid_issue_reference_accepted(self):
        request = IssueExplanationRequest(owner="acme", repo="widget", issue_number=42)
        assert request.issue_number == 42


class TestSaveIssueBounds:
    def test_accepts_a_realistic_bookmark(self):
        request = SaveIssueRequest(
            repo_full_name="acme/widget",
            issue_number=42,
            title="Fix a typo in the README",
            html_url="https://github.com/acme/widget/issues/42",
        )
        assert request.issue_number == 42

    def test_rejects_overlong_title(self):
        with pytest.raises(ValidationError):
            SaveIssueRequest(
                repo_full_name="acme/widget", issue_number=1, title="t" * 501
            )

    def test_rejects_nonpositive_issue_number(self):
        with pytest.raises(ValidationError):
            SaveIssueRequest(repo_full_name="acme/widget", issue_number=0)


class TestCommitMessageBounds:
    def test_existing_text_caps_still_enforced(self):
        with pytest.raises(ValidationError):
            CommitMessageRequest(
                change_description="d", diff_text="x" * 10001, repo_full_name="acme/widget"
            )

    def test_issue_number_must_be_positive_when_given(self):
        with pytest.raises(ValidationError):
            CommitMessageRequest(
                change_description="d", repo_full_name="acme/widget", issue_number=0
            )

    def test_issue_number_optional(self):
        request = CommitMessageRequest(
            change_description="d", repo_full_name="acme/widget"
        )
        assert request.issue_number is None

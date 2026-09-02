"""Tests for the Commit Message Agent and its coordinator integration.

Unit tests only — no network access, no ADK runner.
"""

import pytest

from app.models.schemas import CommitMessageRequest, CommitMessageResponse


# ---------- Schema validation ----------


class TestCommitMessageRequest:
    def test_minimal_valid(self):
        req = CommitMessageRequest(
            change_description="Fix the retry logic",
            repo_full_name="owner/repo",
        )
        assert req.diff_text == ""
        assert req.issue_number is None
        assert req.issue_title == ""

    def test_full_request(self):
        req = CommitMessageRequest(
            diff_text="- old\n+ new",
            change_description="Replace deprecated API call",
            repo_full_name="acme/widget",
            issue_title="Deprecate old API",
            issue_number=42,
        )
        assert req.issue_number == 42
        assert req.repo_full_name == "acme/widget"

    def test_diff_text_max_length(self):
        with pytest.raises(Exception):
            CommitMessageRequest(
                diff_text="x" * 10001,
                change_description="Change",
                repo_full_name="o/r",
            )

    def test_change_description_max_length(self):
        with pytest.raises(Exception):
            CommitMessageRequest(
                change_description="x" * 2001,
                repo_full_name="o/r",
            )


class TestCommitMessageResponse:
    def test_defaults(self):
        resp = CommitMessageResponse(
            subject="feat: add retry logic",
            full_message="feat: add retry logic",
        )
        assert resp.body == ""
        assert resp.commit_type == "feat"
        assert resp.scope == ""
        assert resp.breaking_change is False
        assert resp.alternatives == []

    def test_extra_fields_ignored(self):
        resp = CommitMessageResponse(
            subject="fix: crash on empty input",
            full_message="fix: crash on empty input",
            unknown_key="ignored",
        )
        assert not hasattr(resp, "unknown_key")

    def test_full_response(self):
        resp = CommitMessageResponse(
            subject="fix(auth): handle expired tokens gracefully",
            body="Expired tokens now return a 401 instead of crashing.\n\nCloses #99",
            full_message="fix(auth): handle expired tokens gracefully\n\nExpired tokens now return a 401 instead of crashing.\n\nCloses #99",
            commit_type="fix",
            scope="auth",
            breaking_change=False,
            alternatives=["chore(auth): clean up token handling"],
        )
        assert resp.scope == "auth"
        assert len(resp.alternatives) == 1


# ---------- _fallback_commit_message ----------


class TestFallbackCommitMessage:
    def _req(self, desc: str, title: str = "", issue: int | None = None) -> CommitMessageRequest:
        return CommitMessageRequest(
            change_description=desc,
            repo_full_name="owner/repo",
            issue_title=title,
            issue_number=issue,
        )

    def test_fix_keyword_sets_type(self):
        from app.agents.coordinator import _fallback_commit_message
        result = _fallback_commit_message(self._req("fix crash when input is None"))
        assert result.commit_type == "fix"
        assert result.subject.startswith("fix:")

    def test_docs_keyword_sets_type(self):
        from app.agents.coordinator import _fallback_commit_message
        result = _fallback_commit_message(self._req("update README with new instructions"))
        assert result.commit_type == "docs"

    def test_test_keyword_sets_type(self):
        from app.agents.coordinator import _fallback_commit_message
        result = _fallback_commit_message(self._req("add pytest coverage for the parser"))
        assert result.commit_type == "test"

    def test_chore_keyword_sets_type(self):
        from app.agents.coordinator import _fallback_commit_message
        result = _fallback_commit_message(self._req("bump dependency versions"))
        assert result.commit_type == "chore"

    def test_perf_keyword_sets_type(self):
        from app.agents.coordinator import _fallback_commit_message
        result = _fallback_commit_message(self._req("optimize cache to improve performance"))
        assert result.commit_type == "perf"

    def test_refactor_keyword_sets_type(self):
        from app.agents.coordinator import _fallback_commit_message
        result = _fallback_commit_message(self._req("refactor auth middleware"))
        assert result.commit_type == "refactor"

    def test_default_type_is_feat(self):
        from app.agents.coordinator import _fallback_commit_message
        result = _fallback_commit_message(self._req("add new export button"))
        assert result.commit_type == "feat"

    def test_subject_within_72_chars(self):
        from app.agents.coordinator import _fallback_commit_message
        long_desc = "add a very long feature description that exceeds the 72 character commit message limit by far"
        result = _fallback_commit_message(self._req(long_desc))
        assert len(result.subject) <= 72

    def test_issue_number_in_body(self):
        from app.agents.coordinator import _fallback_commit_message
        result = _fallback_commit_message(self._req("fix crash", issue=99))
        assert "99" in result.body

    def test_full_message_matches_subject_and_body(self):
        from app.agents.coordinator import _fallback_commit_message
        result = _fallback_commit_message(self._req("add retry logic", "Add retry to API client", issue=5))
        assert result.subject in result.full_message

    def test_alternatives_always_returned(self):
        from app.agents.coordinator import _fallback_commit_message
        result = _fallback_commit_message(self._req("fix bug"))
        assert len(result.alternatives) >= 1

    def test_issue_title_used_for_subject(self):
        from app.agents.coordinator import _fallback_commit_message
        result = _fallback_commit_message(self._req("fix it", title="Handle null pointer in parser"))
        assert "null pointer" in result.subject.lower() or "handle" in result.subject.lower()


# ---------- build_commit_agent factory ----------


class TestBuildCommitAgent:
    def test_creates_agent_instance(self):
        from google.adk.agents import Agent
        from app.agents.commit_agent import build_commit_agent

        agent = build_commit_agent("fake-token")
        assert isinstance(agent, Agent)

    def test_agent_name(self):
        from app.agents.commit_agent import build_commit_agent

        agent = build_commit_agent("fake-token")
        assert agent.name == "commit_agent"

    def test_different_tokens_yield_distinct_agents(self):
        from app.agents.commit_agent import build_commit_agent

        a1 = build_commit_agent("token-alice")
        a2 = build_commit_agent("token-bob")
        assert a1 is not a2

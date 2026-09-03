"""Tests for the mentor endpoint's conversation identity.

mentor_session keys conversations by username, so whatever the endpoint passes as
`username` decides who can read whose chat history. The endpoint used to read
`request.state.session` — which nothing in the app ever populates, the only
middleware being CORS — and fall back to `f"user-{token[:8]}"`. GitHub tokens carry
a fixed 4-character prefix (`gho_`, `ghu_`, `ghp_`), so that fallback was the prefix
plus four characters for every user, and it changed whenever a token rotated.
"""

import pytest
from fastapi import HTTPException

from app.api import mentor
from app.api.github_auth import GitHubIdentity


@pytest.fixture
def captured(monkeypatch):
    """Capture the arguments the endpoint hands to run_mentor_chat."""
    calls: list[dict] = []

    async def fake_run(**kwargs):
        calls.append(kwargs)
        from app.models.schemas import MentorChatResponse

        return MentorChatResponse(response="ok", session_active=True)

    import app.agents.coordinator as coordinator

    monkeypatch.setattr(coordinator, "run_mentor_chat", fake_run)
    return calls


def _body(**overrides):
    from app.models.schemas import MentorChatRequest

    payload = {"owner": "acme", "repo": "widget", "issue_number": 1, "message": "hi"}
    payload.update(overrides)
    return MentorChatRequest(**payload)


class TestMentorIdentity:
    async def test_uses_real_github_login(self, monkeypatch, captured):
        async def fake_identity(authorization):
            return GitHubIdentity(token="gho_aaaabbbbcccc", username="octocat")

        monkeypatch.setattr(mentor, "resolve_github_identity", fake_identity)

        await mentor.mentor_chat(_body(), authorization="Bearer gho_aaaabbbbcccc")

        assert captured[0]["username"] == "octocat"

    async def test_distinct_users_get_distinct_keys_despite_token_prefix(
        self, monkeypatch, captured
    ):
        """Two GitHub tokens sharing their first 8 characters must not share a session."""
        identities = iter(
            [
                GitHubIdentity(token="gho_abcd1111", username="alice"),
                GitHubIdentity(token="gho_abcd2222", username="bob"),
            ]
        )

        async def fake_identity(authorization):
            return next(identities)

        monkeypatch.setattr(mentor, "resolve_github_identity", fake_identity)

        await mentor.mentor_chat(_body(), authorization="Bearer gho_abcd1111")
        await mentor.mentor_chat(_body(), authorization="Bearer gho_abcd2222")

        assert captured[0]["username"] != captured[1]["username"]
        assert {c["username"] for c in captured} == {"alice", "bob"}

    async def test_never_derives_identity_from_the_token(self, monkeypatch, captured):
        async def fake_identity(authorization):
            return GitHubIdentity(token="gho_secrettoken", username="octocat")

        monkeypatch.setattr(mentor, "resolve_github_identity", fake_identity)

        await mentor.mentor_chat(_body(), authorization="Bearer gho_secrettoken")

        assert "gho_" not in captured[0]["username"]
        assert not captured[0]["username"].startswith("user-")

    async def test_passes_the_validated_token_through(self, monkeypatch, captured):
        async def fake_identity(authorization):
            return GitHubIdentity(token="gho_validated", username="octocat")

        monkeypatch.setattr(mentor, "resolve_github_identity", fake_identity)

        await mentor.mentor_chat(_body(), authorization="Bearer gho_validated")

        assert captured[0]["github_token"] == "gho_validated"

    async def test_auth_failure_propagates(self, monkeypatch, captured):
        async def fake_identity(authorization):
            raise HTTPException(status_code=401, detail="nope")

        monkeypatch.setattr(mentor, "resolve_github_identity", fake_identity)

        with pytest.raises(HTTPException) as exc:
            await mentor.mentor_chat(_body(), authorization="Bearer bad")
        assert exc.value.status_code == 401
        assert captured == []

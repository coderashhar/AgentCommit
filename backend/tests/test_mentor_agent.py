"""Tests for the Mentor Agent, session store, and schemas.

Unit tests only — no network access, no ADK runner.
"""

import time

import pytest

from app.models.schemas import MentorChatRequest, MentorChatResponse


# ---------- Schema validation ----------


class TestMentorChatRequest:
    def test_valid_request(self):
        req = MentorChatRequest(
            owner="torvalds",
            repo="linux",
            issue_number=42,
            message="Where should I start?",
        )
        assert req.owner == "torvalds"
        assert req.issue_number == 42

    def test_message_max_length(self):
        with pytest.raises(Exception):
            MentorChatRequest(
                owner="o",
                repo="r",
                issue_number=1,
                message="x" * 2001,
            )

    def test_message_at_limit_is_valid(self):
        req = MentorChatRequest(
            owner="o",
            repo="r",
            issue_number=1,
            message="x" * 2000,
        )
        assert len(req.message) == 2000


class TestMentorChatResponse:
    def test_defaults(self):
        resp = MentorChatResponse(response="Hello!")
        assert resp.session_active is True

    def test_session_inactive(self):
        resp = MentorChatResponse(response="Session expired.", session_active=False)
        assert resp.session_active is False


# ---------- Session store ----------


class TestMentorSession:
    def setup_method(self):
        # Clear all sessions before each test using the private dict.
        import app.agents.mentor_session as ms
        ms._sessions.clear()

    def test_get_returns_none_when_absent(self):
        from app.agents.mentor_session import get_session_id
        assert get_session_id("alice", "owner", "repo", 1) is None

    def test_store_and_retrieve(self):
        from app.agents.mentor_session import get_session_id, store_session_id
        store_session_id("alice", "owner", "repo", 1, "session-abc")
        assert get_session_id("alice", "owner", "repo", 1) == "session-abc"

    def test_different_users_isolated(self):
        from app.agents.mentor_session import get_session_id, store_session_id
        store_session_id("alice", "owner", "repo", 1, "session-alice")
        store_session_id("bob", "owner", "repo", 1, "session-bob")
        assert get_session_id("alice", "owner", "repo", 1) == "session-alice"
        assert get_session_id("bob", "owner", "repo", 1) == "session-bob"

    def test_different_issues_isolated(self):
        from app.agents.mentor_session import get_session_id, store_session_id
        store_session_id("alice", "owner", "repo", 1, "session-1")
        store_session_id("alice", "owner", "repo", 2, "session-2")
        assert get_session_id("alice", "owner", "repo", 1) == "session-1"
        assert get_session_id("alice", "owner", "repo", 2) == "session-2"

    def test_expired_session_returns_none(self, monkeypatch):
        from app.agents.mentor_session import get_session_id, store_session_id
        import app.agents.mentor_session as ms

        store_session_id("alice", "owner", "repo", 1, "session-old")

        # Move the clock past TTL
        monkeypatch.setattr(
            ms,
            "SESSION_TTL_SECONDS",
            -1,  # Already expired
        )
        # Also backdate the entry's created_at so TTL check fails
        key = "alice:owner/repo#1"
        ms._sessions[key].created_at = time.monotonic() - 7200  # 2 hours ago

        assert get_session_id("alice", "owner", "repo", 1) is None

    def test_expired_session_is_removed(self, monkeypatch):
        from app.agents.mentor_session import get_session_id, store_session_id
        import app.agents.mentor_session as ms

        store_session_id("alice", "owner", "repo", 1, "session-old")
        key = "alice:owner/repo#1"
        ms._sessions[key].created_at = time.monotonic() - 7200

        get_session_id("alice", "owner", "repo", 1)
        assert key not in ms._sessions

    def test_clear_session(self):
        from app.agents.mentor_session import get_session_id, store_session_id, clear_session
        store_session_id("alice", "owner", "repo", 1, "session-abc")
        clear_session("alice", "owner", "repo", 1)
        assert get_session_id("alice", "owner", "repo", 1) is None

    def test_clear_nonexistent_is_noop(self):
        from app.agents.mentor_session import clear_session
        clear_session("alice", "owner", "repo", 99)  # Should not raise

    def test_active_session_count(self):
        from app.agents.mentor_session import store_session_id, active_session_count
        import app.agents.mentor_session as ms

        store_session_id("alice", "owner", "repo", 1, "s1")
        store_session_id("alice", "owner", "repo", 2, "s2")
        # Expire one manually
        ms._sessions["alice:owner/repo#2"].created_at = time.monotonic() - 7200

        assert active_session_count() == 1


# ---------- build_mentor_agent factory ----------


class TestBuildMentorAgent:
    def test_creates_agent_instance(self):
        from google.adk.agents import Agent
        from app.agents.mentor_agent import build_mentor_agent

        agent = build_mentor_agent("fake-token")
        assert isinstance(agent, Agent)

    def test_agent_name(self):
        from app.agents.mentor_agent import build_mentor_agent

        agent = build_mentor_agent("fake-token")
        assert agent.name == "mentor_agent"

    def test_different_tokens_yield_distinct_agents(self):
        from app.agents.mentor_agent import build_mentor_agent

        a1 = build_mentor_agent("token-alice")
        a2 = build_mentor_agent("token-bob")
        assert a1 is not a2


# ---------- Session store capacity ----------


class TestMentorSessionCapacity:
    """The store expired entries lazily on read, so a conversation nobody returned
    to was never looked up again and sat in the dict for the life of the process."""

    def setup_method(self):
        import app.agents.mentor_session as ms

        ms._sessions.clear()

    def test_no_sweep_below_threshold(self):
        import app.agents.mentor_session as ms

        for i in range(10):
            ms.store_session_id("alice", "owner", "repo", i, f"s{i}")
        # Backdate them all; nothing should be swept yet because we are under threshold.
        for entry in ms._sessions.values():
            entry.created_at = time.monotonic() - 7200
        ms.store_session_id("alice", "owner", "repo", 999, "s999")
        assert len(ms._sessions) == 11

    def test_sweep_drops_expired_once_over_threshold(self, monkeypatch):
        import app.agents.mentor_session as ms

        monkeypatch.setattr(ms, "SWEEP_THRESHOLD", 5)
        for i in range(5):
            ms.store_session_id("alice", "owner", "repo", i, f"s{i}")
        for entry in ms._sessions.values():
            entry.created_at = time.monotonic() - 7200

        ms.store_session_id("alice", "owner", "repo", 100, "fresh")

        assert ms.active_session_count() == 1
        assert ms.get_session_id("alice", "owner", "repo", 100) == "fresh"

    def test_live_sessions_survive_a_sweep(self, monkeypatch):
        import app.agents.mentor_session as ms

        monkeypatch.setattr(ms, "SWEEP_THRESHOLD", 3)
        ms.store_session_id("alice", "owner", "repo", 1, "live")
        for i in range(2, 5):
            ms.store_session_id("alice", "owner", "repo", i, f"s{i}")
            ms._sessions[f"alice:owner/repo#{i}"].created_at = time.monotonic() - 7200

        ms.store_session_id("bob", "owner", "repo", 1, "also-live")

        assert ms.get_session_id("alice", "owner", "repo", 1) == "live"
        assert ms.get_session_id("bob", "owner", "repo", 1) == "also-live"

    def test_hard_cap_evicts_oldest_when_all_are_live(self, monkeypatch):
        """Sustained traffic must not grow the store without limit."""
        import app.agents.mentor_session as ms

        monkeypatch.setattr(ms, "SWEEP_THRESHOLD", 4)
        monkeypatch.setattr(ms, "MAX_SESSIONS", 4)

        for i in range(6):
            ms.store_session_id("alice", "owner", "repo", i, f"s{i}")
            # Stagger ages so "oldest" is well defined.
            ms._sessions[f"alice:owner/repo#{i}"].created_at = time.monotonic() - (100 - i)

        assert len(ms._sessions) <= ms.MAX_SESSIONS + 1
        # The most recent write always survives.
        assert ms.get_session_id("alice", "owner", "repo", 5) == "s5"
        # The oldest is gone.
        assert ms.get_session_id("alice", "owner", "repo", 0) is None

"""Tests for app.api.rate_limit — per-user quota on the agent-backed routes."""

import pytest
from fastapi import HTTPException

from app.api import rate_limit
from app.api.github_auth import GitHubIdentity
from app.api.rate_limit import authorize_agent_request, enforce_rate_limit
from app.tools.utils import CACHE_SCHEMA_VERSION


class _FakePipeline:
    def __init__(self, store: dict, fail: Exception | None = None):
        self._store = store
        self._fail = fail
        self._key: str | None = None

    def incr(self, key):
        self._key = key
        return self

    def expire(self, key, seconds):
        self._store.setdefault("_ttl", {})[key] = seconds
        return self

    async def execute(self):
        if self._fail is not None:
            raise self._fail
        self._store[self._key] = self._store.get(self._key, 0) + 1
        return [self._store[self._key], True]


class _FakeRedis:
    def __init__(self, fail: Exception | None = None):
        self.store: dict = {}
        self._fail = fail

    def pipeline(self):
        return _FakePipeline(self.store, self._fail)


@pytest.fixture
def redis(monkeypatch):
    client = _FakeRedis()

    async def fake_get_redis():
        return client

    monkeypatch.setattr(rate_limit, "get_redis", fake_get_redis)
    return client


class TestEnforceRateLimit:
    async def test_allows_up_to_the_limit(self, redis):
        for _ in range(3):
            await enforce_rate_limit("alice", "agent", limit=3, window_seconds=60)

    async def test_rejects_past_the_limit(self, redis):
        for _ in range(3):
            await enforce_rate_limit("alice", "agent", limit=3, window_seconds=60)
        with pytest.raises(HTTPException) as exc:
            await enforce_rate_limit("alice", "agent", limit=3, window_seconds=60)
        assert exc.value.status_code == 429

    async def test_429_carries_retry_after(self, redis):
        await enforce_rate_limit("alice", "agent", limit=1, window_seconds=60)
        with pytest.raises(HTTPException) as exc:
            await enforce_rate_limit("alice", "agent", limit=1, window_seconds=60)
        retry_after = int(exc.value.headers["Retry-After"])
        assert 0 < retry_after <= 60

    async def test_users_have_separate_quotas(self, redis):
        await enforce_rate_limit("alice", "agent", limit=1, window_seconds=60)
        # bob must be unaffected by alice exhausting hers
        await enforce_rate_limit("bob", "agent", limit=1, window_seconds=60)

    async def test_buckets_are_separate(self, redis):
        await enforce_rate_limit("alice", "agent", limit=1, window_seconds=60)
        await enforce_rate_limit("alice", "other", limit=1, window_seconds=60)

    async def test_key_is_versioned_and_namespaced(self, redis):
        await enforce_rate_limit("alice", "agent", limit=5, window_seconds=60)
        key = next(k for k in redis.store if k != "_ttl")
        assert key.startswith(f"agentcommit:{CACHE_SCHEMA_VERSION}:ratelimit:agent:alice:")

    async def test_ttl_set_on_every_call(self, redis):
        """A key that lost its expiry would lock the user out permanently."""
        await enforce_rate_limit("alice", "agent", limit=5, window_seconds=60)
        await enforce_rate_limit("alice", "agent", limit=5, window_seconds=60)
        assert set(redis.store["_ttl"].values()) == {60}

    async def test_window_rolls_over(self, monkeypatch, redis):
        clock = {"now": 1_000_000}
        monkeypatch.setattr(rate_limit.time, "time", lambda: clock["now"])

        await enforce_rate_limit("alice", "agent", limit=1, window_seconds=60)
        with pytest.raises(HTTPException):
            await enforce_rate_limit("alice", "agent", limit=1, window_seconds=60)

        clock["now"] += 60  # next window
        await enforce_rate_limit("alice", "agent", limit=1, window_seconds=60)

    async def test_fails_open_when_redis_is_down(self, monkeypatch):
        async def broken_get_redis():
            raise OSError("redis unreachable")

        monkeypatch.setattr(rate_limit, "get_redis", broken_get_redis)
        # Must not raise — a Redis blip should not become an outage.
        for _ in range(50):
            await enforce_rate_limit("alice", "agent", limit=1, window_seconds=60)


class TestAuthorizeAgentRequest:
    async def test_returns_identity_when_within_quota(self, monkeypatch, redis):
        async def fake_identity(authorization):
            return GitHubIdentity(token="gho_abc", username="octocat")

        monkeypatch.setattr(rate_limit, "resolve_github_identity", fake_identity)
        identity = await authorize_agent_request("Bearer gho_abc")
        assert identity.username == "octocat"
        assert identity.token == "gho_abc"

    async def test_raises_429_once_quota_is_spent(self, monkeypatch, redis):
        async def fake_identity(authorization):
            return GitHubIdentity(token="gho_abc", username="octocat")

        monkeypatch.setattr(rate_limit, "resolve_github_identity", fake_identity)
        for _ in range(rate_limit.AGENT_REQUESTS_PER_WINDOW):
            await authorize_agent_request("Bearer gho_abc")
        with pytest.raises(HTTPException) as exc:
            await authorize_agent_request("Bearer gho_abc")
        assert exc.value.status_code == 429

    async def test_quota_is_not_spent_when_auth_fails(self, monkeypatch, redis):
        async def rejecting(authorization):
            raise HTTPException(status_code=401, detail="nope")

        monkeypatch.setattr(rate_limit, "resolve_github_identity", rejecting)
        with pytest.raises(HTTPException) as exc:
            await authorize_agent_request("Bearer bad")
        assert exc.value.status_code == 401
        assert redis.store == {}

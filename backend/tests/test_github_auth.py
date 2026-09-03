"""Tests for app.api.github_auth — token validation, identity resolution, caching."""

import hashlib

import httpx
import pytest
from fastapi import HTTPException

from app.api import github_auth
from app.api.github_auth import (
    GitHubIdentity,
    _extract_token,
    _identity_cache_key,
    require_github_token,
    resolve_github_identity,
)
from app.tools.utils import CACHE_SCHEMA_VERSION


class _FakeResponse:
    """Minimal stand-in for httpx.Response."""

    def __init__(self, status_code: int, payload=None, raises: bool = False):
        self.status_code = status_code
        self._payload = payload
        self._raises = raises

    def json(self):
        if self._raises:
            raise ValueError("not json")
        return self._payload


class _FakeClient:
    """Async context manager standing in for httpx.AsyncClient."""

    def __init__(self, response=None, error: Exception | None = None):
        self._response = response
        self._error = error
        self.calls: list[tuple[str, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, headers=None):
        self.calls.append((url, headers or {}))
        if self._error is not None:
            raise self._error
        return self._response


@pytest.fixture
def no_cache(monkeypatch):
    """Cache misses on read, records writes — isolates tests from a live Redis."""
    writes: list[tuple[str, dict, int]] = []

    async def fake_get(key):
        return None

    async def fake_set(key, value, ttl_seconds=3600):
        writes.append((key, value, ttl_seconds))

    monkeypatch.setattr(github_auth, "cache_get", fake_get)
    monkeypatch.setattr(github_auth, "cache_set", fake_set)
    return writes


def _install_client(monkeypatch, client: _FakeClient) -> None:
    monkeypatch.setattr(github_auth.httpx, "AsyncClient", lambda **kw: client)


# ---------- _extract_token ----------


class TestExtractToken:
    def test_strips_bearer_prefix(self):
        assert _extract_token("Bearer gho_abc123") == "gho_abc123"

    def test_accepts_bare_token(self):
        assert _extract_token("gho_abc123") == "gho_abc123"

    def test_strips_surrounding_whitespace(self):
        assert _extract_token("Bearer   gho_abc123  ") == "gho_abc123"

    def test_empty_header_rejected(self):
        with pytest.raises(HTTPException) as exc:
            _extract_token("Bearer ")
        assert exc.value.status_code == 401

    def test_whitespace_only_rejected(self):
        with pytest.raises(HTTPException) as exc:
            _extract_token("   ")
        assert exc.value.status_code == 401


# ---------- _identity_cache_key ----------


class TestIdentityCacheKey:
    def test_token_never_appears_in_key(self):
        """The raw token must not be recoverable from the cache key."""
        token = "gho_supersecret"
        assert token not in _identity_cache_key(token)

    def test_key_is_sha256_of_token(self):
        token = "gho_abc123"
        expected = hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert _identity_cache_key(token).endswith(expected)

    def test_versioned_and_namespaced(self):
        key = _identity_cache_key("gho_abc123")
        assert key.startswith(f"agentcommit:{CACHE_SCHEMA_VERSION}:identity:")

    def test_distinct_tokens_distinct_keys(self):
        assert _identity_cache_key("token_a") != _identity_cache_key("token_b")


# ---------- resolve_github_identity ----------


class TestResolveGitHubIdentity:
    async def test_returns_token_and_username(self, monkeypatch, no_cache):
        _install_client(monkeypatch, _FakeClient(_FakeResponse(200, {"login": "octocat"})))
        identity = await resolve_github_identity("Bearer gho_abc")
        assert identity == GitHubIdentity(token="gho_abc", username="octocat")

    async def test_single_round_trip(self, monkeypatch, no_cache):
        """One GitHub call yields both facts — the defect this replaced made two."""
        client = _FakeClient(_FakeResponse(200, {"login": "octocat"}))
        _install_client(monkeypatch, client)
        await resolve_github_identity("Bearer gho_abc")
        assert len(client.calls) == 1

    async def test_sends_bearer_header(self, monkeypatch, no_cache):
        client = _FakeClient(_FakeResponse(200, {"login": "octocat"}))
        _install_client(monkeypatch, client)
        await resolve_github_identity("Bearer gho_abc")
        _, headers = client.calls[0]
        assert headers["Authorization"] == "Bearer gho_abc"

    async def test_caches_successful_validation(self, monkeypatch, no_cache):
        _install_client(monkeypatch, _FakeClient(_FakeResponse(200, {"login": "octocat"})))
        await resolve_github_identity("Bearer gho_abc")
        assert len(no_cache) == 1
        key, value, ttl = no_cache[0]
        assert value == {"username": "octocat"}
        assert ttl == github_auth._IDENTITY_TTL_SECONDS

    async def test_cache_hit_skips_github(self, monkeypatch):
        async def fake_get(key):
            return {"username": "cached-user"}

        async def fake_set(key, value, ttl_seconds=3600):  # pragma: no cover
            raise AssertionError("must not write on a cache hit")

        monkeypatch.setattr(github_auth, "cache_get", fake_get)
        monkeypatch.setattr(github_auth, "cache_set", fake_set)
        client = _FakeClient(_FakeResponse(200, {"login": "live-user"}))
        _install_client(monkeypatch, client)

        identity = await resolve_github_identity("Bearer gho_abc")
        assert identity.username == "cached-user"
        assert client.calls == []

    async def test_cache_entry_without_username_ignored(self, monkeypatch):
        """A malformed cache entry must fall through to GitHub, not authenticate as ''."""
        async def fake_get(key):
            return {"username": ""}

        async def fake_set(key, value, ttl_seconds=3600):
            return None

        monkeypatch.setattr(github_auth, "cache_get", fake_get)
        monkeypatch.setattr(github_auth, "cache_set", fake_set)
        client = _FakeClient(_FakeResponse(200, {"login": "live-user"}))
        _install_client(monkeypatch, client)

        identity = await resolve_github_identity("Bearer gho_abc")
        assert identity.username == "live-user"
        assert len(client.calls) == 1

    async def test_rejected_token_is_401(self, monkeypatch, no_cache):
        _install_client(monkeypatch, _FakeClient(_FakeResponse(401)))
        with pytest.raises(HTTPException) as exc:
            await resolve_github_identity("Bearer gho_bad")
        assert exc.value.status_code == 401

    async def test_failed_validation_is_not_cached(self, monkeypatch, no_cache):
        """A rejection must be re-checked next request, not remembered for the TTL."""
        _install_client(monkeypatch, _FakeClient(_FakeResponse(401)))
        with pytest.raises(HTTPException):
            await resolve_github_identity("Bearer gho_bad")
        assert no_cache == []

    async def test_github_unreachable_is_503(self, monkeypatch, no_cache):
        _install_client(monkeypatch, _FakeClient(error=httpx.ConnectError("boom")))
        with pytest.raises(HTTPException) as exc:
            await resolve_github_identity("Bearer gho_abc")
        assert exc.value.status_code == 503

    async def test_200_without_login_is_401(self, monkeypatch, no_cache):
        """An empty username would scope every saved row to "" — reject instead."""
        _install_client(monkeypatch, _FakeClient(_FakeResponse(200, {})))
        with pytest.raises(HTTPException) as exc:
            await resolve_github_identity("Bearer gho_abc")
        assert exc.value.status_code == 401
        assert no_cache == []

    async def test_200_with_null_login_is_401(self, monkeypatch, no_cache):
        _install_client(monkeypatch, _FakeClient(_FakeResponse(200, {"login": None})))
        with pytest.raises(HTTPException) as exc:
            await resolve_github_identity("Bearer gho_abc")
        assert exc.value.status_code == 401

    async def test_200_with_unparseable_body_is_401(self, monkeypatch, no_cache):
        _install_client(monkeypatch, _FakeClient(_FakeResponse(200, raises=True)))
        with pytest.raises(HTTPException) as exc:
            await resolve_github_identity("Bearer gho_abc")
        assert exc.value.status_code == 401

    async def test_empty_header_never_calls_github(self, monkeypatch, no_cache):
        client = _FakeClient(_FakeResponse(200, {"login": "octocat"}))
        _install_client(monkeypatch, client)
        with pytest.raises(HTTPException):
            await resolve_github_identity("Bearer ")
        assert client.calls == []


# ---------- require_github_token ----------


class TestRequireGitHubToken:
    async def test_returns_only_the_token(self, monkeypatch, no_cache):
        _install_client(monkeypatch, _FakeClient(_FakeResponse(200, {"login": "octocat"})))
        assert await require_github_token("Bearer gho_abc") == "gho_abc"

    async def test_shares_validation_rules(self, monkeypatch, no_cache):
        """The thin wrapper must not weaken the checks it delegates to."""
        _install_client(monkeypatch, _FakeClient(_FakeResponse(200, {})))
        with pytest.raises(HTTPException) as exc:
            await require_github_token("Bearer gho_abc")
        assert exc.value.status_code == 401

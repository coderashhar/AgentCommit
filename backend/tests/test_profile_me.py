"""Tests for GET /api/profile/me — the GitHub profile behind the dashboard card.

The dashboard used to hardcode public_repos/followers/following to 0 because the
NextAuth session carries only name, image and login. This endpoint supplies the real
values.
"""

import pytest
from fastapi import HTTPException

from app.api import profile as profile_api
from app.api.github_auth import GitHubIdentity
from app.api.profile import _to_user_profile, get_current_user_profile

# A realistic /users/{login} payload. GitHub sends JSON null for every optional
# text field, which is the part most likely to break the projection.
GITHUB_PAYLOAD = {
    "login": "coderashhar",
    "name": "Mohd. Ashhar Khan",
    "avatar_url": "https://avatars.githubusercontent.com/u/152192451?v=4",
    "bio": "CSE (AI & ML) undergrad",
    "public_repos": 36,
    "followers": 3,
    "following": 2,
    "html_url": "https://github.com/coderashhar",
    "company": None,
    "location": None,
    "blog": None,
}


@pytest.fixture
def identity(monkeypatch):
    async def fake_identity(authorization):
        return GitHubIdentity(token="gho_abc", username="coderashhar")

    monkeypatch.setattr(profile_api, "resolve_github_identity", fake_identity)


@pytest.fixture
def no_cache(monkeypatch):
    writes: list[tuple[str, dict, int]] = []

    async def fake_get(key):
        return None

    async def fake_set(key, value, ttl_seconds=3600):
        writes.append((key, value, ttl_seconds))

    monkeypatch.setattr(profile_api, "cache_get", fake_get)
    monkeypatch.setattr(profile_api, "cache_set", fake_set)
    return writes


def _install_fetch(monkeypatch, payload, calls=None):
    async def fake_fetch(username, token):
        if calls is not None:
            calls.append((username, token))
        return payload

    monkeypatch.setattr(profile_api, "fetch_github_profile", fake_fetch)


class TestToUserProfile:
    def test_maps_the_counts_the_card_renders(self):
        p = _to_user_profile(GITHUB_PAYLOAD, "fallback")
        assert (p.public_repos, p.followers, p.following) == (36, 3, 2)

    def test_null_text_fields_become_empty_not_none(self):
        """bio is typed str, so a JSON null must be coerced or validation fails."""
        p = _to_user_profile({"login": "x", "bio": None, "name": None}, "x")
        assert p.bio == ""
        assert p.name == ""

    def test_nullable_fields_stay_none(self):
        p = _to_user_profile(GITHUB_PAYLOAD, "fallback")
        assert p.company is None and p.location is None and p.blog is None

    def test_missing_counts_default_to_zero(self):
        p = _to_user_profile({"login": "x"}, "x")
        assert (p.public_repos, p.followers, p.following) == (0, 0, 0)

    def test_falls_back_to_the_authenticated_login(self):
        assert _to_user_profile({}, "coderashhar").username == "coderashhar"

    def test_empty_blog_normalises_to_none(self):
        assert _to_user_profile({"login": "x", "blog": ""}, "x").blog is None


class TestGetCurrentUserProfile:
    async def test_returns_the_real_counts(self, monkeypatch, identity, no_cache):
        _install_fetch(monkeypatch, GITHUB_PAYLOAD)
        response = await get_current_user_profile(authorization="Bearer gho_abc")
        import json

        body = json.loads(response.body)
        assert body["public_repos"] == 36
        assert body["followers"] == 3
        assert body["following"] == 2

    async def test_caches_the_result(self, monkeypatch, identity, no_cache):
        _install_fetch(monkeypatch, GITHUB_PAYLOAD)
        await get_current_user_profile(authorization="Bearer gho_abc")
        assert len(no_cache) == 1
        _, value, ttl = no_cache[0]
        assert value["followers"] == 3
        assert ttl == profile_api._PROFILE_CACHE_TTL_SECONDS

    async def test_cache_hit_skips_github(self, monkeypatch, identity):
        cached = {"username": "coderashhar", "followers": 99}

        async def fake_get(key):
            return cached

        async def fake_set(key, value, ttl_seconds=3600):  # pragma: no cover
            raise AssertionError("must not write on a cache hit")

        monkeypatch.setattr(profile_api, "cache_get", fake_get)
        monkeypatch.setattr(profile_api, "cache_set", fake_set)

        calls: list = []
        _install_fetch(monkeypatch, GITHUB_PAYLOAD, calls)

        response = await get_current_user_profile(authorization="Bearer gho_abc")
        import json

        assert json.loads(response.body)["followers"] == 99
        assert calls == []

    async def test_github_error_payload_is_502(self, monkeypatch, identity, no_cache):
        _install_fetch(monkeypatch, {"error": "GitHub API failed with status 403"})
        with pytest.raises(HTTPException) as exc:
            await get_current_user_profile(authorization="Bearer gho_abc")
        assert exc.value.status_code == 502
        assert no_cache == []

    async def test_does_not_consume_agent_quota(self, monkeypatch, identity, no_cache):
        """This is a plain GitHub read; it must not spend the Gemini rate-limit budget."""
        _install_fetch(monkeypatch, GITHUB_PAYLOAD)

        async def boom(*args, **kwargs):  # pragma: no cover
            raise AssertionError("agent rate limiter must not run for /profile/me")

        monkeypatch.setattr(profile_api, "authorize_agent_request", boom)
        await get_current_user_profile(authorization="Bearer gho_abc")

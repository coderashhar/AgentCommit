"""GitHub token validation helpers for protected API routes."""

import hashlib
import logging
from typing import NamedTuple

import httpx
from fastapi import HTTPException

from app.tools.utils import CACHE_SCHEMA_VERSION, cache_get, cache_set

logger = logging.getLogger(__name__)

_GITHUB_USER_URL = "https://api.github.com/user"

# How long a validated token is trusted without re-asking GitHub. Before this cache,
# every protected route spent a full GitHub round-trip on validation alone, against
# the user's own rate limit — and `saved.py` spent two, because it re-fetched the
# same response to read `login`. The trade is bounded staleness: a token revoked on
# GitHub keeps working here for at most this long. Keep it short.
_IDENTITY_TTL_SECONDS = 300


class GitHubIdentity(NamedTuple):
    """A validated GitHub access token and the login that owns it."""

    token: str
    username: str


def _identity_cache_key(token: str) -> str:
    """Build the cache key for a token, hashing it first.

    The token itself is never stored — not as a value and not as a key. Redis is not
    a credential store, and anything able to enumerate keys would otherwise be able
    to read live access tokens.
    """
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"agentcommit:{CACHE_SCHEMA_VERSION}:identity:{digest}"


def _extract_token(authorization: str) -> str:
    """Pull the bearer token out of an Authorization header value."""
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    return token


async def resolve_github_identity(authorization: str) -> GitHubIdentity:
    """Validate a GitHub bearer token and return it with its owner's login.

    One GitHub round-trip produces both facts, cached for `_IDENTITY_TTL_SECONDS`.
    Callers that need only the token should use `require_github_token`.

    Raises:
        HTTPException: 401 if the header is empty, the token is rejected, or GitHub
            returns no login for it; 503 if GitHub is unreachable.
    """
    token = _extract_token(authorization)
    cache_key = _identity_cache_key(token)

    cached = await cache_get(cache_key)
    if cached and cached.get("username"):
        return GitHubIdentity(token=token, username=cached["username"])

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                _GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
            )
    except httpx.RequestError as e:
        logger.warning("GitHub token validation request failed: %s", str(e))
        raise HTTPException(
            status_code=503,
            detail="Could not validate GitHub session. Please try again.",
        ) from e

    if response.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="GitHub session expired or token invalid. Please log out and log back in.",
        )

    try:
        username = (response.json() or {}).get("login") or ""
    except ValueError:
        username = ""

    if not username:
        # A 200 carrying no login means GitHub returned something we don't understand.
        # Accepting it would let an empty username reach the database layer, where it
        # scopes every row to "" — one shared bucket across callers.
        logger.warning("GitHub returned 200 with no login during token validation")
        raise HTTPException(status_code=401, detail="Could not identify user from token.")

    # Only successful validations are cached. A rejection must be re-checked on the
    # next request, so a user who reconnects their account isn't locked out for the TTL.
    await cache_set(cache_key, {"username": username}, ttl_seconds=_IDENTITY_TTL_SECONDS)

    return GitHubIdentity(token=token, username=username)


async def require_github_token(authorization: str) -> str:
    """Validate a GitHub bearer token and return it.

    For routes that need the token but not the login; shares the cache and the
    validation rules of `resolve_github_identity`.
    """
    identity = await resolve_github_identity(authorization)
    return identity.token

"""Per-user rate limiting for the agent-backed routes.

Every agent route spends a Gemini call and several GitHub calls, both against
quotas shared by all users of a deployment. Without a limit, one account — or one
runaway client retrying in a loop — exhausts the free tier for everyone, and the
only symptom is that all other users silently drop onto the deterministic fallback.
"""

import logging
import time

from fastapi import HTTPException
from redis.exceptions import RedisError

from app.api.github_auth import GitHubIdentity, resolve_github_identity
from app.tools.utils import CACHE_SCHEMA_VERSION, get_redis

logger = logging.getLogger(__name__)

# The dashboard fires three agent requests in sequence on load and the mentor panel
# is interactive, so the window has to absorb bursts. This is a backstop against
# runaway clients, not a product limit.
AGENT_REQUESTS_PER_WINDOW = 30
AGENT_WINDOW_SECONDS = 60


async def enforce_rate_limit(
    username: str,
    bucket: str,
    limit: int,
    window_seconds: int,
) -> None:
    """Consume one unit of a user's quota, raising 429 when it is exhausted.

    A fixed window, one Redis key per user per bucket per window. Fixed windows admit
    up to 2x the limit across a window boundary; that is an acceptable trade here
    against the extra round-trips a sliding window costs, because the point is to
    stop a runaway loop rather than to meter precisely.

    Fails open. If Redis is unreachable the request proceeds, matching how the cache
    layer degrades — a limiter that failed closed would turn a Redis blip into a full
    outage, which is worse than the burst it prevents.
    """
    now = int(time.time())
    window_index = now // window_seconds
    key = (
        f"agentcommit:{CACHE_SCHEMA_VERSION}:ratelimit:"
        f"{bucket}:{username}:{window_index}"
    )

    try:
        client = await get_redis()
        pipe = client.pipeline()
        pipe.incr(key)
        # Set the TTL every time rather than only on creation: a key that somehow
        # loses its expiry would otherwise block the user permanently.
        pipe.expire(key, window_seconds)
        count = (await pipe.execute())[0]
    except (OSError, RedisError) as e:
        logger.warning("Rate limit check failed open for %s: %s", username, str(e))
        return

    if count > limit:
        retry_after = window_seconds - (now % window_seconds)
        logger.info("Rate limit hit for %s on bucket %s (%d/%d)", username, bucket, count, limit)
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment and try again.",
            headers={"Retry-After": str(retry_after)},
        )


async def authorize_agent_request(authorization: str) -> GitHubIdentity:
    """Validate the caller and consume one unit of their agent quota.

    The identity lookup is cached, so this costs no extra GitHub round-trip beyond
    what validation already needed.
    """
    identity = await resolve_github_identity(authorization)
    await enforce_rate_limit(
        identity.username,
        bucket="agent",
        limit=AGENT_REQUESTS_PER_WINDOW,
        window_seconds=AGENT_WINDOW_SECONDS,
    )
    return identity

"""GitHub token validation helpers for protected API routes."""

import logging

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def require_github_token(authorization: str) -> str:
    """Extract and validate a GitHub bearer token from an Authorization header."""
    token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.github.com/user",
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

    return token

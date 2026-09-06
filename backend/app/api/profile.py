"""Profile analysis endpoints — triggers the Profile Analyzer Agent."""

import logging

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from app.api.github_auth import resolve_github_identity
from app.api.rate_limit import authorize_agent_request
from app.models.schemas import ProfileAnalysisRequest, ProfileAnalysisResponse, UserProfile
from app.tools.github_tool import fetch_github_profile
from app.tools.utils import build_cache_key, cache_get, cache_set

logger = logging.getLogger(__name__)

router = APIRouter()

# Follower and repository counts drift slowly and are decoration on the dashboard,
# not something a decision depends on.
_PROFILE_CACHE_TTL_SECONDS = 900


def _to_user_profile(payload: dict, fallback_username: str) -> UserProfile:
    """Project a GitHub /users/{login} payload onto the wire schema.

    GitHub returns JSON null for every optional text field, so the ones typed as
    plain strings here have to be coerced — passing None straight through fails
    validation and would turn a decorative profile card into a 500.
    """
    return UserProfile(
        username=payload.get("login") or fallback_username,
        name=payload.get("name") or "",
        avatar_url=payload.get("avatar_url") or "",
        bio=payload.get("bio") or "",
        public_repos=payload.get("public_repos") or 0,
        followers=payload.get("followers") or 0,
        following=payload.get("following") or 0,
        html_url=payload.get("html_url") or "",
        company=payload.get("company"),
        location=payload.get("location"),
        blog=payload.get("blog") or None,
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    authorization: str = Header(..., description="GitHub access token"),
) -> JSONResponse:
    """Return the authenticated user's GitHub profile.

    Separate from /analyze because this is a plain GitHub read with no agent behind
    it — it must not consume the caller's agent rate-limit quota, and it must stay
    fast when Gemini is unavailable.
    """
    identity = await resolve_github_identity(authorization)

    cache_key = build_cache_key("ghprofile", identity.username)
    cached = await cache_get(cache_key)
    if cached:
        return JSONResponse(content=cached)

    payload = await fetch_github_profile(identity.username, identity.token)
    if not isinstance(payload, dict) or payload.get("error"):
        logger.warning(
            "GitHub profile fetch failed for %s: %s",
            identity.username,
            (payload or {}).get("error") if isinstance(payload, dict) else "no payload",
        )
        raise HTTPException(status_code=502, detail="Could not load your GitHub profile.")

    profile = _to_user_profile(payload, identity.username).model_dump()
    await cache_set(cache_key, profile, ttl_seconds=_PROFILE_CACHE_TTL_SECONDS)
    return JSONResponse(content=profile)


@router.post("/analyze")
async def analyze_profile(
    request: ProfileAnalysisRequest,
    authorization: str = Header(..., description="GitHub access token"),
) -> JSONResponse:
    """Analyze a GitHub user's profile to extract skills, experience, and interests.

    Triggers the Profile Analyzer Agent via Google ADK.
    """
    token = (await authorize_agent_request(authorization)).token

    # Import here to avoid circular imports during startup
    from app.agents.coordinator import run_profile_analysis

    try:
        result = await run_profile_analysis(
            username=request.username,
            github_token=token,
        )
        return JSONResponse(content=result.model_dump())
    except Exception:
        logger.exception("Profile analysis failed")
        raise HTTPException(status_code=500, detail="Profile analysis failed. Please try again.")

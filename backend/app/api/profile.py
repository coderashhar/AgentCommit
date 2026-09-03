"""Profile analysis endpoints — triggers the Profile Analyzer Agent."""

import logging

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from app.api.rate_limit import authorize_agent_request
from app.models.schemas import ProfileAnalysisRequest, ProfileAnalysisResponse

logger = logging.getLogger(__name__)

router = APIRouter()


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

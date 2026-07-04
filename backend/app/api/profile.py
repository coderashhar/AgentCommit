"""Profile analysis endpoints — triggers the Profile Analyzer Agent."""

import logging

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from app.api.github_auth import require_github_token
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
    token = await require_github_token(authorization)

    # Import here to avoid circular imports during startup
    from app.agents.coordinator import run_profile_analysis

    try:
        result = await run_profile_analysis(
            username=request.username,
            github_token=token,
        )
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        import traceback
        logger.error("Profile analysis failed: %s", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Backend Error: {str(e)}")

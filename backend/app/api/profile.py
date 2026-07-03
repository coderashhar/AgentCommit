"""Profile analysis endpoints — triggers the Profile Analyzer Agent."""

from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import ProfileAnalysisRequest, ProfileAnalysisResponse

router = APIRouter()


@router.post("/analyze", response_model=ProfileAnalysisResponse)
async def analyze_profile(
    request: ProfileAnalysisRequest,
    authorization: str = Header(..., description="GitHub access token"),
) -> ProfileAnalysisResponse:
    """Analyze a GitHub user's profile to extract skills, experience, and interests.

    Triggers the Profile Analyzer Agent via Google ADK.
    """
    token = authorization.replace("Bearer ", "")

    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    # Import here to avoid circular imports during startup
    from app.agents.coordinator import run_profile_analysis

    result = await run_profile_analysis(
        username=request.username,
        github_token=token,
    )

    return result

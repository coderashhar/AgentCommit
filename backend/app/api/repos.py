"""Repository recommendation endpoints — triggers the Repo Recommendation Agent."""

from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import (
    RepoRecommendationRequest,
    RepoRecommendationResponse,
)

router = APIRouter()


@router.post("/recommend", response_model=RepoRecommendationResponse)
async def recommend_repos(
    request: RepoRecommendationRequest,
    authorization: str = Header(..., description="GitHub access token"),
) -> RepoRecommendationResponse:
    """Recommend open source repositories based on user's skill profile.

    Triggers the Repo Recommendation Agent via Google ADK.
    """
    token = authorization.replace("Bearer ", "")

    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    from app.agents.coordinator import run_repo_recommendation

    result = await run_repo_recommendation(
        languages=request.languages,
        frameworks=request.frameworks,
        experience_level=request.experience_level,
        domains=request.domains,
        github_token=token,
    )

    return result

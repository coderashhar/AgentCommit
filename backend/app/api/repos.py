"""Repository recommendation endpoints — triggers the Repo Recommendation Agent."""

import logging

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from app.api.github_auth import require_github_token
from app.models.schemas import (
    RepoRecommendationRequest,
    RepoRecommendationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/recommend")
async def recommend_repos(
    request: RepoRecommendationRequest,
    authorization: str = Header(..., description="GitHub access token"),
) -> JSONResponse:
    """Recommend open source repositories based on user's skill profile.

    Triggers the Repo Recommendation Agent via Google ADK.
    """
    token = await require_github_token(authorization)

    from app.agents.coordinator import run_repo_recommendation

    try:
        result = await run_repo_recommendation(
            languages=request.languages,
            frameworks=request.frameworks,
            experience_level=request.experience_level,
            domains=request.domains,
            github_token=token,
        )
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        import traceback
        logger.error("Repo recommendation failed: %s", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Backend Error: {str(e)}")

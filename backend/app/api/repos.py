"""Repository recommendation endpoints — triggers the Repo Recommendation Agent."""

import logging

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from app.api.rate_limit import authorize_agent_request
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
    token = (await authorize_agent_request(authorization)).token

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
    except Exception:
        logger.exception("Repo recommendation failed")
        raise HTTPException(status_code=500, detail="Repo recommendation failed. Please try again.")

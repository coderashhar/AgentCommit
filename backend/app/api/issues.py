"""Issue discovery and explanation endpoints."""

import logging

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from app.api.github_auth import require_github_token
from app.models.schemas import (
    IssueDiscoveryRequest,
    IssueDiscoveryResponse,
    IssueExplanationRequest,
    IssueExplanationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/discover")
async def discover_issues(
    request: IssueDiscoveryRequest,
    authorization: str = Header(..., description="GitHub access token"),
) -> JSONResponse:
    """Discover beginner-friendly issues matching the user's skills.

    Triggers the Issue Discovery Agent via Google ADK.
    """
    token = await require_github_token(authorization)

    from app.agents.coordinator import run_issue_discovery

    try:
        result = await run_issue_discovery(
            repositories=request.repositories,
            languages=request.languages,
            experience_level=request.experience_level,
            github_token=token,
        )
        return JSONResponse(content=result.model_dump())
    except Exception:
        logger.exception("Issue discovery failed")
        raise HTTPException(status_code=500, detail="Issue discovery failed. Please try again.")


@router.post("/explain")
async def explain_issue(
    request: IssueExplanationRequest,
    authorization: str = Header(..., description="GitHub access token"),
) -> JSONResponse:
    """Generate an AI-powered explanation of a GitHub issue.

    Triggers the Issue Explainer Agent via Google ADK.
    """
    token = await require_github_token(authorization)

    from app.agents.coordinator import run_issue_explanation

    try:
        result = await run_issue_explanation(
            owner=request.owner,
            repo=request.repo,
            issue_number=request.issue_number,
            github_token=token,
        )
        return JSONResponse(content=result.model_dump())
    except Exception:
        logger.exception("Issue explanation failed")
        raise HTTPException(status_code=500, detail="Issue explanation failed. Please try again.")

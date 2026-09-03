"""Issue discovery and explanation endpoints."""

import logging

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from app.api.rate_limit import authorize_agent_request
from app.models.schemas import (
    IssueDiscoveryRequest,
    IssueDiscoveryResponse,
    IssueExplanationRequest,
    IssueExplanationResponse,
    ImplementationPlanRequest,
    ImplementationPlanResponse,
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
    token = (await authorize_agent_request(authorization)).token

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
    token = (await authorize_agent_request(authorization)).token

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


@router.post("/plan")
async def generate_implementation_plan(
    request: ImplementationPlanRequest,
    authorization: str = Header(..., description="GitHub access token"),
) -> JSONResponse:
    """Generate a step-by-step implementation plan for a GitHub issue.

    Triggers the Implementation Planner Agent via Google ADK.
    """
    token = (await authorize_agent_request(authorization)).token

    from app.agents.coordinator import run_implementation_plan

    try:
        result = await run_implementation_plan(
            owner=request.owner,
            repo=request.repo,
            issue_number=request.issue_number,
            github_token=token,
        )
        return JSONResponse(content=result.model_dump())
    except Exception:
        logger.exception("Implementation plan generation failed")
        raise HTTPException(status_code=500, detail="Implementation plan generation failed. Please try again.")

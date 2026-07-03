"""Issue discovery and explanation endpoints."""

from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import (
    IssueDiscoveryRequest,
    IssueDiscoveryResponse,
    IssueExplanationRequest,
    IssueExplanationResponse,
)

router = APIRouter()


@router.post("/discover", response_model=IssueDiscoveryResponse)
async def discover_issues(
    request: IssueDiscoveryRequest,
    authorization: str = Header(..., description="GitHub access token"),
) -> IssueDiscoveryResponse:
    """Discover beginner-friendly issues matching the user's skills.

    Triggers the Issue Discovery Agent via Google ADK.
    """
    token = authorization.replace("Bearer ", "")

    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    from app.agents.coordinator import run_issue_discovery

    result = await run_issue_discovery(
        repositories=request.repositories,
        languages=request.languages,
        experience_level=request.experience_level,
        github_token=token,
    )

    return result


@router.post("/explain", response_model=IssueExplanationResponse)
async def explain_issue(
    request: IssueExplanationRequest,
    authorization: str = Header(..., description="GitHub access token"),
) -> IssueExplanationResponse:
    """Generate an AI-powered explanation of a GitHub issue.

    Triggers the Issue Explainer Agent via Google ADK.
    """
    token = authorization.replace("Bearer ", "")

    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    from app.agents.coordinator import run_issue_explanation

    result = await run_issue_explanation(
        owner=request.owner,
        repo=request.repo,
        issue_number=request.issue_number,
        github_token=token,
    )

    return result

"""Commit message generation endpoint."""

import logging

from fastapi import APIRouter, Header, HTTPException

from app.api.github_auth import require_github_token
from app.models.schemas import CommitMessageRequest, CommitMessageResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate")
async def generate_commit_message(
    request: CommitMessageRequest,
    authorization: str = Header(..., description="GitHub access token"),
) -> CommitMessageResponse:
    """Generate a conventional commit message from a diff or change description.

    Triggers the Commit Message Agent via Google ADK. Falls back to a keyword
    heuristic if the agent is unavailable.
    """
    token = await require_github_token(authorization)

    from app.agents.coordinator import run_commit_message

    try:
        return await run_commit_message(request=request, github_token=token)
    except Exception:
        logger.exception("Commit message generation failed")
        raise HTTPException(status_code=500, detail="Commit message generation failed. Please try again.")

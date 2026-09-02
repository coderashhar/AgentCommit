"""Mentor chat endpoint — conversational guidance for GitHub issues."""

import logging

from fastapi import APIRouter, Header, HTTPException, Request

from app.api.github_auth import require_github_token
from app.models.schemas import MentorChatRequest, MentorChatResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat")
async def mentor_chat(
    request_body: MentorChatRequest,
    request: Request,
    authorization: str = Header(..., description="GitHub access token"),
) -> MentorChatResponse:
    """Send a message to the Mentor Agent and get a conversational response.

    Conversations are session-based: follow-up messages about the same issue
    are answered with full context of the prior turns.
    """
    token = await require_github_token(authorization)

    # Extract the authenticated username from the session stored at login.
    # Fall back to "anonymous" if unavailable — session key will be per-token.
    session = getattr(request.state, "session", None)
    username: str = "anonymous"
    if session and isinstance(session, dict):
        username = session.get("username", "anonymous")

    # Also check the request's auth header for the token-derived identity.
    # The token itself uniquely identifies the user, so use it as fallback key.
    if username == "anonymous":
        username = f"user-{token[:8]}"

    from app.agents.coordinator import run_mentor_chat

    try:
        result = await run_mentor_chat(
            owner=request_body.owner,
            repo=request_body.repo,
            issue_number=request_body.issue_number,
            user_message=request_body.message,
            username=username,
            github_token=token,
        )
        return result
    except Exception:
        logger.exception("Mentor chat failed")
        raise HTTPException(status_code=500, detail="Mentor chat failed. Please try again.")

"""Mentor chat endpoint — conversational guidance for GitHub issues."""

import logging

from fastapi import APIRouter, Header, HTTPException

from app.api.rate_limit import authorize_agent_request
from app.models.schemas import MentorChatRequest, MentorChatResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat")
async def mentor_chat(
    request_body: MentorChatRequest,
    authorization: str = Header(..., description="GitHub access token"),
) -> MentorChatResponse:
    """Send a message to the Mentor Agent and get a conversational response.

    Conversations are session-based: follow-up messages about the same issue
    are answered with full context of the prior turns.
    """
    # The GitHub login is the conversation's identity. It has to be the real login:
    # mentor_session keys conversations by it, so two users who resolve to the same
    # value would read each other's conversation history.
    identity = await authorize_agent_request(authorization)

    from app.agents.coordinator import run_mentor_chat

    try:
        result = await run_mentor_chat(
            owner=request_body.owner,
            repo=request_body.repo,
            issue_number=request_body.issue_number,
            user_message=request_body.message,
            username=identity.username,
            github_token=identity.token,
        )
        return result
    except Exception:
        logger.exception("Mentor chat failed")
        raise HTTPException(status_code=500, detail="Mentor chat failed. Please try again.")

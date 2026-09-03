"""Saved issues endpoints — bookmark and list issues a user wants to revisit."""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.github_auth import resolve_github_identity
from app.database.connection import get_session
from app.database.crud import delete_saved_issue, get_saved_issues, save_issue
from app.models.schemas import SaveIssueRequest, SavedIssueResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_response(row) -> SavedIssueResponse:
    """Project a SavedIssue row onto the wire schema."""
    return SavedIssueResponse(
        repo_full_name=row.repo_full_name,
        issue_number=row.issue_number,
        title=row.title or "",
        html_url=row.html_url or "",
        saved_at=row.saved_at.isoformat() if row.saved_at else "",
    )


@router.post("/issues", response_model=SavedIssueResponse, status_code=201)
async def bookmark_issue(
    request: SaveIssueRequest,
    authorization: str = Header(..., description="GitHub access token"),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Bookmark an issue so it persists across sessions."""
    identity = await resolve_github_identity(authorization)

    try:
        row = await save_issue(
            session,
            username=identity.username,
            repo_full_name=request.repo_full_name,
            issue_number=request.issue_number,
            title=request.title,
            html_url=request.html_url,
        )
    except Exception:
        logger.exception("Failed to save issue")
        raise HTTPException(status_code=500, detail="Failed to save issue.")

    return JSONResponse(status_code=201, content=_to_response(row).model_dump())


@router.get("/issues", response_model=list[SavedIssueResponse])
async def list_saved_issues(
    authorization: str = Header(..., description="GitHub access token"),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Return all issues bookmarked by the authenticated user."""
    identity = await resolve_github_identity(authorization)

    try:
        rows = await get_saved_issues(session, identity.username)
    except Exception:
        logger.exception("Failed to list saved issues")
        raise HTTPException(status_code=500, detail="Failed to retrieve saved issues.")

    return JSONResponse(content=[_to_response(row).model_dump() for row in rows])


@router.delete("/issues/{repo_owner}/{repo_name}/{issue_number}", status_code=204)
async def unsave_issue(
    repo_owner: str,
    repo_name: str,
    issue_number: int,
    authorization: str = Header(..., description="GitHub access token"),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Remove a bookmarked issue."""
    identity = await resolve_github_identity(authorization)

    try:
        deleted = await delete_saved_issue(
            session,
            username=identity.username,
            repo_full_name=f"{repo_owner}/{repo_name}",
            issue_number=issue_number,
        )
    except Exception:
        logger.exception("Failed to delete saved issue")
        raise HTTPException(status_code=500, detail="Failed to remove saved issue.")

    if not deleted:
        raise HTTPException(status_code=404, detail="Saved issue not found.")

    return JSONResponse(status_code=204, content=None)

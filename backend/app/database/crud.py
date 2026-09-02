"""CRUD operations for AgentCommit's PostgreSQL tables.

All functions are async and accept an AsyncSession. They are intentionally
thin — no business logic, no network calls. The coordinator and API routers
call these; the session lifecycle is managed by the FastAPI dependency
`get_session()` from `app.database.connection`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ProfileAnalysis, SavedIssue, User
from app.models.schemas import ProfileAnalysisResponse

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Users                                                                        #
# --------------------------------------------------------------------------- #


async def upsert_user(
    session: AsyncSession,
    *,
    github_id: int,
    username: str,
    name: str = "",
    avatar_url: str = "",
    bio: str = "",
    access_token: str,
) -> User:
    """Insert a new user or update their token and metadata on conflict."""
    stmt = (
        pg_insert(User)
        .values(
            github_id=github_id,
            username=username,
            name=name,
            avatar_url=avatar_url,
            bio=bio,
            access_token=access_token,
        )
        .on_conflict_do_update(
            index_elements=["github_id"],
            set_={
                "username": username,
                "name": name,
                "avatar_url": avatar_url,
                "bio": bio,
                "access_token": access_token,
                "updated_at": datetime.now(timezone.utc),
            },
        )
        .returning(User)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar_one()


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


# --------------------------------------------------------------------------- #
#  Profile analyses                                                             #
# --------------------------------------------------------------------------- #


async def save_profile_analysis(
    session: AsyncSession,
    username: str,
    analysis: ProfileAnalysisResponse,
) -> ProfileAnalysis:
    """Persist a profile analysis result.  Appends a new row; history is kept."""
    row = ProfileAnalysis(
        username=username,
        languages=analysis.languages,
        frameworks=analysis.frameworks,
        experience_level=analysis.experience_level,
        domains=analysis.domains,
        summary=analysis.summary,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_latest_profile_analysis(
    session: AsyncSession, username: str
) -> ProfileAnalysis | None:
    """Return the most recently saved analysis for *username*, or None."""
    result = await session.execute(
        select(ProfileAnalysis)
        .where(ProfileAnalysis.username == username)
        .order_by(ProfileAnalysis.analyzed_at.desc(), ProfileAnalysis.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# --------------------------------------------------------------------------- #
#  Saved issues                                                                 #
# --------------------------------------------------------------------------- #


async def save_issue(
    session: AsyncSession,
    *,
    username: str,
    repo_full_name: str,
    issue_number: int,
    title: str = "",
    html_url: str = "",
) -> SavedIssue:
    """Bookmark an issue for a user.  Idempotent: skips if already saved."""
    existing_result = await session.execute(
        select(SavedIssue).where(
            SavedIssue.username == username,
            SavedIssue.repo_full_name == repo_full_name,
            SavedIssue.issue_number == issue_number,
        )
    )
    existing_row = existing_result.scalar_one_or_none()
    if existing_row is not None:
        return existing_row  # already saved

    row = SavedIssue(
        username=username,
        repo_full_name=repo_full_name,
        issue_number=issue_number,
        title=title,
        html_url=html_url,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_saved_issues(session: AsyncSession, username: str) -> list[SavedIssue]:
    """Return all saved issues for *username*, newest first."""
    result = await session.execute(
        select(SavedIssue)
        .where(SavedIssue.username == username)
        .order_by(SavedIssue.saved_at.desc())
    )
    return list(result.scalars().all())


async def delete_saved_issue(
    session: AsyncSession,
    *,
    username: str,
    repo_full_name: str,
    issue_number: int,
) -> bool:
    """Remove a saved issue.  Returns True if a row was deleted, False otherwise."""
    result = await session.execute(
        delete(SavedIssue).where(
            SavedIssue.username == username,
            SavedIssue.repo_full_name == repo_full_name,
            SavedIssue.issue_number == issue_number,
        )
    )
    await session.commit()
    return result.rowcount > 0

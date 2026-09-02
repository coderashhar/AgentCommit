"""Tests for CRUD operations using an in-memory SQLite database.

SQLite is used instead of PostgreSQL so these tests run without a live database.
The PostgreSQL-specific `pg_insert(...).on_conflict_do_update` in upsert_user
is not supported by SQLite, so upsert_user is tested separately via direct inserts.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base, SavedIssue
from app.database.crud import (
    get_latest_profile_analysis,
    get_saved_issues,
    delete_saved_issue,
    save_profile_analysis,
    save_issue,
)
from app.models.schemas import ProfileAnalysisResponse


@pytest_asyncio.fixture
async def session():
    """In-memory SQLite async session for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


@pytest.fixture
def sample_analysis() -> ProfileAnalysisResponse:
    return ProfileAnalysisResponse(
        username="alice",
        languages=["Python", "JavaScript"],
        frameworks=["FastAPI", "React"],
        experience_level="intermediate",
        domains=["web development"],
        top_repositories=["alice/project-a"],
        summary="Alice is an intermediate developer.",
    )


# ---------- Profile analysis ----------


@pytest.mark.asyncio
async def test_save_and_get_profile_analysis(session, sample_analysis):
    row = await save_profile_analysis(session, "alice", sample_analysis)
    assert row.id is not None
    assert row.username == "alice"
    assert row.experience_level == "intermediate"

    fetched = await get_latest_profile_analysis(session, "alice")
    assert fetched is not None
    assert fetched.languages == ["Python", "JavaScript"]


@pytest.mark.asyncio
async def test_get_latest_returns_most_recent(session, sample_analysis):
    await save_profile_analysis(session, "alice", sample_analysis)
    updated = ProfileAnalysisResponse(
        username="alice",
        languages=["Rust"],
        frameworks=[],
        experience_level="advanced",
        domains=[],
        top_repositories=[],
        summary="Updated.",
    )
    await save_profile_analysis(session, "alice", updated)

    fetched = await get_latest_profile_analysis(session, "alice")
    assert fetched is not None
    assert fetched.experience_level == "advanced"


@pytest.mark.asyncio
async def test_get_profile_analysis_none_when_absent(session):
    result = await get_latest_profile_analysis(session, "nobody")
    assert result is None


# ---------- Saved issues ----------


@pytest.mark.asyncio
async def test_save_and_list_issues(session):
    await save_issue(
        session,
        username="alice",
        repo_full_name="example/project",
        issue_number=42,
        title="Fix typo",
        html_url="https://github.com/example/project/issues/42",
    )
    await save_issue(
        session,
        username="alice",
        repo_full_name="example/project",
        issue_number=99,
        title="Add docs",
        html_url="https://github.com/example/project/issues/99",
    )

    rows = await get_saved_issues(session, "alice")
    assert len(rows) == 2
    issue_numbers = {row.issue_number for row in rows}
    assert {42, 99} == issue_numbers


@pytest.mark.asyncio
async def test_save_issue_idempotent(session):
    await save_issue(
        session, username="alice", repo_full_name="example/project", issue_number=42
    )
    # Saving the same issue again should not create a duplicate
    await save_issue(
        session, username="alice", repo_full_name="example/project", issue_number=42
    )
    rows = await get_saved_issues(session, "alice")
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_delete_saved_issue(session):
    await save_issue(
        session, username="alice", repo_full_name="example/project", issue_number=42
    )
    deleted = await delete_saved_issue(
        session, username="alice", repo_full_name="example/project", issue_number=42
    )
    assert deleted is True
    rows = await get_saved_issues(session, "alice")
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_issue_returns_false(session):
    deleted = await delete_saved_issue(
        session, username="alice", repo_full_name="example/project", issue_number=999
    )
    assert deleted is False


@pytest.mark.asyncio
async def test_saved_issues_scoped_to_user(session):
    await save_issue(
        session, username="alice", repo_full_name="example/project", issue_number=1
    )
    await save_issue(
        session, username="bob", repo_full_name="example/project", issue_number=2
    )
    alice_issues = await get_saved_issues(session, "alice")
    bob_issues = await get_saved_issues(session, "bob")
    assert len(alice_issues) == 1
    assert len(bob_issues) == 1
    assert alice_issues[0].issue_number == 1
    assert bob_issues[0].issue_number == 2

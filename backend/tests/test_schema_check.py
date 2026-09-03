"""Tests for app.database.schema_check — startup schema-drift reporting.

Migrations are applied by a release command, not by the app, so the app can boot
against a database that is behind the code. This check exists to make that one loud
startup line instead of a stream of failed queries inside requests.
"""

import logging

import pytest
from sqlalchemy.exc import OperationalError

from app.database import schema_check
from app.database.schema_check import expected_head_revision, verify_schema_is_current


@pytest.fixture
def head(monkeypatch):
    monkeypatch.setattr(schema_check, "expected_head_revision", lambda: "abc123")
    return "abc123"


def _set_current(monkeypatch, value=None, error=None):
    async def fake_current():
        if error is not None:
            raise error
        return value

    monkeypatch.setattr(schema_check, "current_database_revision", fake_current)


class TestExpectedHeadRevision:
    def test_reads_the_real_migration_head(self):
        """The revision on disk must be discoverable, or the check is inert."""
        assert expected_head_revision() == "b28573c7b38c"


class TestVerifySchemaIsCurrent:
    async def test_matching_revision_logs_info(self, monkeypatch, head, caplog):
        _set_current(monkeypatch, value="abc123")
        with caplog.at_level(logging.INFO, logger="app.database.schema_check"):
            await verify_schema_is_current()
        assert "current" in caplog.text
        assert not [r for r in caplog.records if r.levelno >= logging.ERROR]

    async def test_behind_revision_logs_error(self, monkeypatch, head, caplog):
        _set_current(monkeypatch, value="old999")
        with caplog.at_level(logging.INFO, logger="app.database.schema_check"):
            await verify_schema_is_current()
        assert [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert "old999" in caplog.text and "abc123" in caplog.text
        assert "alembic upgrade head" in caplog.text

    async def test_unmigrated_database_logs_error(self, monkeypatch, head, caplog):
        _set_current(monkeypatch, value=None)
        with caplog.at_level(logging.INFO, logger="app.database.schema_check"):
            await verify_schema_is_current()
        assert [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert "alembic upgrade head" in caplog.text

    async def test_unreachable_database_logs_error_without_raising(
        self, monkeypatch, head, caplog
    ):
        _set_current(
            monkeypatch,
            error=OperationalError("SELECT version_num", {}, Exception("down")),
        )
        with caplog.at_level(logging.INFO, logger="app.database.schema_check"):
            await verify_schema_is_current()  # must not raise
        assert [r for r in caplog.records if r.levelno >= logging.ERROR]

    async def test_no_head_revision_is_a_silent_noop(self, monkeypatch, caplog):
        """With no migration scripts readable there is nothing to compare against."""
        monkeypatch.setattr(schema_check, "expected_head_revision", lambda: None)

        async def must_not_run():  # pragma: no cover
            raise AssertionError("must not query the database without a head revision")

        monkeypatch.setattr(schema_check, "current_database_revision", must_not_run)
        with caplog.at_level(logging.INFO, logger="app.database.schema_check"):
            await verify_schema_is_current()
        assert not [r for r in caplog.records if r.levelno >= logging.ERROR]

    async def test_never_raises_on_any_path(self, monkeypatch, head):
        """The app must boot regardless — agent routes do not need PostgreSQL."""
        for outcome in (
            {"value": "abc123"},
            {"value": "old999"},
            {"value": None},
            {"error": OperationalError("q", {}, Exception("down"))},
        ):
            _set_current(monkeypatch, **outcome)
            await verify_schema_is_current()

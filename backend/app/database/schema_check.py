"""Startup check comparing the database's schema revision against the code's.

Migrations are applied by a release command (`alembic upgrade head`), not by the
application, so that N instances starting at once cannot race the same DDL. The
cost of that choice is a failure mode where the code ships ahead of the schema and
every persistence route fails one query at a time, deep inside a request. This check
turns that into one loud line at startup instead.

It only reports. Nothing here creates or alters tables, and a failure never stops
the app from serving — the agent routes work without PostgreSQL, and refusing to
boot would take them down too.
"""

import logging
from pathlib import Path

from sqlalchemy import text

from app.database.connection import async_session

logger = logging.getLogger(__name__)

_ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def expected_head_revision() -> str | None:
    """Read the head revision from the migration scripts on disk."""
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        return ScriptDirectory.from_config(Config(str(_ALEMBIC_INI))).get_current_head()
    except Exception as e:
        logger.warning("Could not read Alembic head revision: %s", str(e))
        return None


async def current_database_revision() -> str | None:
    """Read the revision stamped in the database, or None if it has never migrated."""
    async with async_session() as session:
        result = await session.execute(text("SELECT version_num FROM alembic_version"))
        return result.scalar_one_or_none()


async def verify_schema_is_current() -> None:
    """Log whether the database schema matches the code, without changing either."""
    head = expected_head_revision()
    if head is None:
        return

    try:
        current = await current_database_revision()
    except Exception as e:
        # Deliberately broad. SQLAlchemy wraps most failures in SQLAlchemyError, but
        # connection-time errors from the asyncpg driver — a wrong host, a missing
        # role — surface as asyncpg exceptions instead and would otherwise escape a
        # narrower clause, turning this report into the traceback it exists to avoid.
        logger.error(
            "Could not read the database schema version: %s: %s. "
            "Check DATABASE_URL, then run `alembic upgrade head` from backend/.",
            type(e).__name__,
            str(e),
        )
        return

    if current == head:
        logger.info("Database schema is current (revision %s).", head)
    elif current is None:
        logger.error(
            "Database has no Alembic revision stamped; expected %s. "
            "Run `alembic upgrade head` — every persistence route will fail until you do.",
            head,
        )
    else:
        logger.error(
            "Database schema is at revision %s but this code expects %s. "
            "Run `alembic upgrade head`.",
            current,
            head,
        )

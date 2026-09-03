"""Alembic environment configuration for AgentCommit.

Uses the SQLAlchemy async engine from app.database.connection so that
`alembic revision --autogenerate` produces migrations that match the ORM models,
and `alembic upgrade head` applies them against the same database URL that the app uses.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import Base so Alembic can introspect the ORM models for autogenerate.
from app.config import settings
from app.database.models import Base  # noqa: F401 — side-effect: registers all models

# ---------------------------------------------------------------------------
# Alembic config object — provides access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object that autogenerate compares against the live database.
target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Resolve the database URL so `alembic upgrade head` works in CI/prod without
# anyone editing alembic.ini.
# ---------------------------------------------------------------------------
def _async_url(url: str) -> str:
    """Force the asyncpg driver onto a PostgreSQL URL.

    `run_migrations_online` below builds an *async* engine, so the URL must name an
    async driver. A bare `postgresql://` (the historical alembic.ini default, and the
    form most hosting providers hand out) raises
    "The asyncio extension requires an async driver" without this.
    """
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


# Precedence: DATABASE_URL, then the app's own settings, then alembic.ini. Deriving
# the default from app.config keeps one source of truth, so a developer who edits
# .env does not also have to edit alembic.ini.
database_url = os.environ.get("DATABASE_URL") or settings.database_url
if database_url:
    # set_main_option runs the value through ConfigParser interpolation, so a literal
    # "%" in a percent-encoded password has to be doubled or it raises here.
    config.set_main_option("sqlalchemy.url", _async_url(database_url).replace("%", "%%"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a live connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using the async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

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
# Override sqlalchemy.url from environment if DATABASE_URL is set.
# This lets `alembic upgrade head` in CI/prod pick up the right URL without
# editing alembic.ini.
# ---------------------------------------------------------------------------
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # asyncpg URLs need the sync dialect for Alembic's sync migration runner;
    # swap the driver so both the app (asyncpg) and Alembic (psycopg2 / sync)
    # can coexist. In offline mode we emit SQL, so the URL is used as-is.
    config.set_main_option("sqlalchemy.url", database_url)


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

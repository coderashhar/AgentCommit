"""AgentCommit Backend — FastAPI application entry point."""

import logging
import logging.config
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import auth, profile, repos, issues, saved, mentor, commit

logger = logging.getLogger(__name__)

# Every module calls logging.getLogger(__name__), but without this call nothing was
# ever configured — every logger.warning/logger.info in the app was silently
# discarded, including the Redis fail-open warnings and "agent failed; using
# fallback" messages that are the most important signal in this codebase.
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "INFO",
        },
    }
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown events."""
    # Report, don't migrate. Schema changes are applied by a release command so that
    # concurrent instances cannot race the same DDL; this only says, in one line at
    # startup, whether the database matches the code. It never raises: the agent
    # routes do not need PostgreSQL, so a schema problem must not take them down.
    from app.database.schema_check import verify_schema_is_current

    try:
        await verify_schema_is_current()
    except Exception:
        logger.exception("Schema version check failed; continuing startup")

    yield
    # Shutdown: cleanup resources


app = FastAPI(
    title="AgentCommit API",
    description="AI Open Source Mentor — Backend API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
app.include_router(repos.router, prefix="/api/repos", tags=["Repositories"])
app.include_router(issues.router, prefix="/api/issues", tags=["Issues"])
app.include_router(saved.router, prefix="/api/saved", tags=["Saved"])
app.include_router(mentor.router, prefix="/api/mentor", tags=["Mentor"])
app.include_router(commit.router, prefix="/api/commit", tags=["Commit"])


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "agentcommit-api"}

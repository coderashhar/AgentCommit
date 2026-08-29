"""AgentCommit Backend — FastAPI application entry point."""

import logging.config
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import auth, profile, repos, issues

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
    # Startup: initialize database, redis, etc.
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


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "agentcommit-api"}

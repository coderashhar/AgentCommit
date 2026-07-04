"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""

    # Google AI (Gemini via ADK)
    google_api_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://agentcommit:agentcommit@localhost:5432/agentcommit"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Backend
    backend_url: str = "http://localhost:8000"

    # MCP
    github_mcp_token: str = ""

    model_config = {
        "env_file": (".env", "../.env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()

import os
if settings.google_api_key:
    os.environ["GEMINI_API_KEY"] = settings.google_api_key

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
    cors_origins: list[str] = ["http://localhost:3000"]

    # Backend
    backend_url: str = "http://localhost:8000"

    # MCP
    github_mcp_token: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()

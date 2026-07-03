"""GitHub OAuth authentication endpoints."""

from fastapi import APIRouter, HTTPException
import httpx

from app.config import settings
from app.models.schemas import GitHubAuthRequest, GitHubAuthResponse, UserProfile

router = APIRouter()

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


@router.get("/github/url")
async def get_github_auth_url() -> dict[str, str]:
    """Return the GitHub OAuth authorization URL for the frontend to redirect to."""
    auth_url = (
        f"{GITHUB_AUTH_URL}"
        f"?client_id={settings.github_client_id}"
        f"&scope=read:user,repo,read:org"
        f"&redirect_uri={settings.backend_url}/api/auth/github/callback"
    )
    return {"url": auth_url}


@router.post("/github/callback")
async def github_callback(request: GitHubAuthRequest) -> GitHubAuthResponse:
    """Exchange GitHub OAuth code for an access token and fetch user profile."""
    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_response = await client.post(
            GITHUB_TOKEN_URL,
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": request.code,
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to exchange OAuth code")

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=401, detail="No access token received")

        # Fetch user profile from GitHub
        user_response = await client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )

        if user_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to fetch user profile")

        user_data = user_response.json()

        profile = UserProfile(
            username=user_data["login"],
            name=user_data.get("name", ""),
            avatar_url=user_data.get("avatar_url", ""),
            bio=user_data.get("bio", ""),
            public_repos=user_data.get("public_repos", 0),
            followers=user_data.get("followers", 0),
            following=user_data.get("following", 0),
            html_url=user_data.get("html_url", ""),
            company=user_data.get("company"),
            location=user_data.get("location"),
            blog=user_data.get("blog"),
        )

        return GitHubAuthResponse(
            access_token=access_token,
            user=profile,
        )

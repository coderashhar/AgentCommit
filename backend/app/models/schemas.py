"""Pydantic models for API request/response validation."""

from pydantic import BaseModel, ConfigDict, Field


# ========================
# Auth Schemas
# ========================

class GitHubAuthRequest(BaseModel):
    """Request body for GitHub OAuth callback."""
    code: str = Field(..., description="GitHub OAuth authorization code")


class UserProfile(BaseModel):
    """GitHub user profile data."""
    username: str
    name: str = ""
    avatar_url: str = ""
    bio: str = ""
    public_repos: int = 0
    followers: int = 0
    following: int = 0
    html_url: str = ""
    company: str | None = None
    location: str | None = None
    blog: str | None = None


class GitHubAuthResponse(BaseModel):
    """Response for successful GitHub OAuth authentication."""
    access_token: str
    user: UserProfile


# ========================
# Profile Analysis Schemas
# ========================

class ProfileAnalysisRequest(BaseModel):
    """Request to analyze a GitHub profile."""
    username: str = Field(..., description="GitHub username to analyze")


class ProfileAnalysisResponse(BaseModel):
    """Result of profile analysis from the Profile Analyzer Agent."""
    model_config = ConfigDict(extra="ignore")

    username: str
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    experience_level: str = Field(default="beginner", description="beginner | intermediate | advanced")
    domains: list[str] = Field(default_factory=list)
    top_repositories: list[str] = Field(default_factory=list)
    summary: str = ""


# ========================
# Repository Recommendation Schemas
# ========================

class RepoRecommendationRequest(BaseModel):
    """Request for repository recommendations based on profile analysis."""
    languages: list[str]
    frameworks: list[str] = Field(default_factory=list)
    experience_level: str = "beginner"
    domains: list[str] = Field(default_factory=list)


class RecommendedRepo(BaseModel):
    """A single recommended repository."""
    model_config = ConfigDict(extra="ignore")

    full_name: str = Field(..., description="owner/repo format")
    description: str = ""
    stars: int = 0
    language: str = ""
    topics: list[str] = Field(default_factory=list)
    open_issues_count: int = 0
    html_url: str = ""
    match_score: float = Field(0.0, description="0-100 relevance score")
    match_reason: str = ""


class RepoRecommendationResponse(BaseModel):
    """List of recommended repositories."""
    repositories: list[RecommendedRepo] = Field(default_factory=list)


# ========================
# Issue Discovery Schemas
# ========================

class IssueDiscoveryRequest(BaseModel):
    """Request to discover beginner-friendly issues."""
    repositories: list[str] = Field(..., description="List of repo full names (owner/repo)")
    languages: list[str] = Field(default_factory=list)
    experience_level: str = "beginner"


class DiscoveredIssue(BaseModel):
    """A single discovered issue."""
    model_config = ConfigDict(extra="ignore")

    title: str
    number: int
    repo_full_name: str
    labels: list[str] = Field(default_factory=list)
    html_url: str = ""
    created_at: str = ""
    comments: int = 0
    body_preview: str = Field("", description="First 200 chars of the issue body")
    difficulty: str = Field("easy", description="easy | medium | hard")
    match_score: float = 0.0


class IssueDiscoveryResponse(BaseModel):
    """List of discovered issues."""
    issues: list[DiscoveredIssue] = Field(default_factory=list)


# ========================
# Issue Explanation Schemas
# ========================

class IssueExplanationRequest(BaseModel):
    """Request to explain a specific GitHub issue."""
    owner: str
    repo: str
    issue_number: int


class IssueExplanationResponse(BaseModel):
    """AI-generated explanation of a GitHub issue."""
    model_config = ConfigDict(extra="ignore")

    title: str
    summary: str = Field("", description="Plain English explanation")
    difficulty: int = Field(1, ge=1, le=5, description="1-5 star difficulty")
    estimated_time: str = Field("", description="e.g., '2 hours'")
    required_concepts: list[str] = Field(default_factory=list)
    learning_resources: list[str] = Field(default_factory=list)
    suggested_approach: str = ""
    files_to_explore: list[str] = Field(default_factory=list)

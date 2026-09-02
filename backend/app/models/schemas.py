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
    forks: int = 0
    pushed_at: str = ""
    tier: str = Field("", description="beginner | intermediate | advanced")
    verified: bool = Field(False, description="Rebuilt from a live GitHub fetch rather than trusted from an LLM")


class RepoRecommendationResponse(BaseModel):
    """List of recommended repositories."""
    repositories: list[RecommendedRepo] = Field(default_factory=list)
    source: str = Field("agent", description="agent | hybrid | deterministic")


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
    updated_at: str = ""
    verified: bool = Field(False, description="Rebuilt from a live GitHub fetch rather than trusted from an LLM")


class IssueDiscoveryResponse(BaseModel):
    """List of discovered issues."""
    issues: list[DiscoveredIssue] = Field(default_factory=list)
    source: str = Field("agent", description="agent | hybrid | deterministic")


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


# ========================
# Implementation Plan Schemas
# ========================

class ImplementationStep(BaseModel):
    """A single step in an implementation plan."""
    model_config = ConfigDict(extra="ignore")

    step_number: int
    title: str
    description: str
    files_to_modify: list[str] = Field(default_factory=list)
    code_hints: str = ""


class ImplementationPlanRequest(BaseModel):
    """Request to generate an implementation plan for a GitHub issue."""
    owner: str
    repo: str
    issue_number: int


class ImplementationPlanResponse(BaseModel):
    """AI-generated implementation plan for a GitHub issue."""
    model_config = ConfigDict(extra="ignore")

    title: str
    issue_summary: str = ""
    steps: list[ImplementationStep] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    edge_cases: list[str] = Field(default_factory=list)
    testing_strategy: str = ""
    estimated_complexity: str = Field("medium", description="low | medium | high")
    prerequisite_knowledge: list[str] = Field(default_factory=list)
    files_overview: list[str] = Field(default_factory=list)


# ========================
# Commit Message Schemas
# ========================

class CommitMessageRequest(BaseModel):
    """Request to generate a conventional commit message."""
    diff_text: str = Field("", max_length=10000, description="Git diff or code changes")
    change_description: str = Field(..., max_length=2000, description="Plain English description of the change")
    repo_full_name: str = Field(..., description="owner/repo format")
    issue_title: str = Field("", description="Title of the related GitHub issue, if any")
    issue_number: int | None = Field(None, description="Related issue number for context")


class CommitMessageResponse(BaseModel):
    """AI-generated conventional commit message."""
    model_config = ConfigDict(extra="ignore")

    subject: str = Field(..., description="Commit subject line (≤72 chars)")
    body: str = Field("", description="Optional multi-line commit body")
    full_message: str = Field(..., description="Complete commit message (subject + body)")
    commit_type: str = Field("feat", description="Conventional commit type: feat|fix|docs|style|refactor|perf|test|chore")
    scope: str = Field("", description="Optional scope in parentheses")
    breaking_change: bool = Field(False, description="Whether this is a breaking change")
    alternatives: list[str] = Field(default_factory=list, description="Alternative subject lines")


# ========================
# Mentor Chat Schemas
# ========================

class MentorChatRequest(BaseModel):
    """Request to send a message to the Mentor Agent."""
    owner: str
    repo: str
    issue_number: int
    message: str = Field(..., max_length=2000, description="User's question or message")


class MentorChatResponse(BaseModel):
    """Response from the Mentor Agent."""
    response: str = Field(..., description="Mentor's plain-text reply")
    session_active: bool = Field(True, description="Whether the session is still alive")


# ========================
# Saved Issues Schemas
# ========================

class SaveIssueRequest(BaseModel):
    """Request to bookmark an issue."""
    repo_full_name: str = Field(..., description="owner/repo format")
    issue_number: int
    title: str = ""
    html_url: str = ""


class SavedIssueResponse(BaseModel):
    """A bookmarked issue."""
    repo_full_name: str
    issue_number: int
    title: str
    html_url: str
    saved_at: str

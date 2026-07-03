/**
 * Shared TypeScript types for AgentCommit frontend.
 *
 * These types mirror the backend Pydantic schemas for type-safe
 * communication between the frontend and FastAPI backend.
 */

// ========================
// Auth Types
// ========================

export interface UserProfile {
  username: string;
  name: string;
  avatar_url: string;
  bio: string;
  public_repos: number;
  followers: number;
  following: number;
  html_url: string;
  company: string | null;
  location: string | null;
  blog: string | null;
}

export interface AuthResponse {
  access_token: string;
  user: UserProfile;
}

// ========================
// Profile Analysis Types
// ========================

export interface ProfileAnalysis {
  username: string;
  languages: string[];
  frameworks: string[];
  experience_level: "beginner" | "intermediate" | "advanced";
  domains: string[];
  top_repositories: string[];
  summary: string;
}

// ========================
// Repository Types
// ========================

export interface RecommendedRepo {
  full_name: string;
  description: string;
  stars: number;
  language: string;
  topics: string[];
  open_issues_count: number;
  html_url: string;
  match_score: number;
  match_reason: string;
}

export interface RepoRecommendationResponse {
  repositories: RecommendedRepo[];
}

// ========================
// Issue Types
// ========================

export interface DiscoveredIssue {
  title: string;
  number: number;
  repo_full_name: string;
  labels: string[];
  html_url: string;
  created_at: string;
  comments: number;
  body_preview: string;
  difficulty: "easy" | "medium" | "hard";
  match_score: number;
}

export interface IssueDiscoveryResponse {
  issues: DiscoveredIssue[];
}

// ========================
// Issue Explanation Types
// ========================

export interface IssueExplanation {
  title: string;
  summary: string;
  difficulty: number;
  estimated_time: string;
  required_concepts: string[];
  learning_resources: string[];
  suggested_approach: string;
  files_to_explore: string[];
}

// ========================
// Agent Status Types
// ========================

export type AgentStatus = "idle" | "running" | "completed" | "error";

export interface AgentActivity {
  name: string;
  status: AgentStatus;
  message: string;
}

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
  forks: number;
  pushed_at: string;
  tier: string;
  verified: boolean;
}

export interface RepoRecommendationResponse {
  repositories: RecommendedRepo[];
  source: "agent" | "hybrid" | "deterministic";
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
  updated_at: string;
  verified: boolean;
}

export interface IssueDiscoveryResponse {
  issues: DiscoveredIssue[];
  source: "agent" | "hybrid" | "deterministic";
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
// Saved Issues Types
// ========================

export interface SaveIssueRequest {
  repo_full_name: string;
  issue_number: number;
  title: string;
  html_url: string;
}

export interface SavedIssueResponse {
  repo_full_name: string;
  issue_number: number;
  title: string;
  html_url: string;
  saved_at: string;
}

// ========================
// Implementation Plan Types
// ========================

export interface ImplementationStep {
  step_number: number;
  title: string;
  description: string;
  files_to_modify: string[];
  code_hints: string;
}

export interface ImplementationPlan {
  title: string;
  issue_summary: string;
  steps: ImplementationStep[];
  risks: string[];
  edge_cases: string[];
  testing_strategy: string;
  estimated_complexity: "low" | "medium" | "high";
  prerequisite_knowledge: string[];
  files_overview: string[];
}

// ========================
// Commit Message Types
// ========================

export interface CommitMessageRequest {
  diff_text?: string;
  change_description: string;
  repo_full_name: string;
  issue_title?: string;
  issue_number?: number;
}

export interface CommitMessageResponse {
  subject: string;
  body: string;
  full_message: string;
  commit_type: string;
  scope: string;
  breaking_change: boolean;
  alternatives: string[];
}

// ========================
// Mentor Chat Types
// ========================

export interface MentorChatRequest {
  owner: string;
  repo: string;
  issue_number: number;
  message: string;
}

export interface MentorChatResponse {
  response: string;
  session_active: boolean;
}

export interface ChatMessage {
  role: "user" | "mentor";
  content: string;
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

/**
 * API client for communication with the AgentCommit FastAPI backend.
 *
 * All functions are typed against the shared interfaces in @/types.
 */

import type {
  AuthResponse,
  ProfileAnalysis,
  RepoRecommendationResponse,
  IssueDiscoveryResponse,
  IssueExplanation,
} from "@/types";
import { API_BASE_URL } from "@/lib/constants";

const API_BASE = API_BASE_URL;

/** FastAPI validation errors return `detail` as an array of {msg, loc, ...} objects. */
function extractErrorDetail(data: unknown): string {
  if (typeof data === "string") return data;
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          item && typeof item === "object" && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : JSON.stringify(item),
        )
        .join("; ");
    }
    if (detail !== undefined) return JSON.stringify(detail);
  }
  return JSON.stringify(data);
}

/**
 * Generic fetch wrapper with error handling and auth headers.
 */
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  const url = `${API_BASE}${endpoint}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw err;
    }
    console.error(`[API] Network error fetching ${url}:`, err);
    throw new Error(
      "Couldn't reach the AgentCommit backend. Check your connection and try again.",
    );
  }

  if (!response.ok) {
    let errorDetail = "Unknown error";
    try {
      const data = await response.clone().json();
      errorDetail = extractErrorDetail(data);
    } catch {
      errorDetail = await response.text(); // Capture the raw HTML or plain text!
    }
    throw new Error(`Request failed (${response.status}): ${errorDetail}`);
  }

  return response.json() as Promise<T>;
}

// ========================
// Auth
// ========================

/**
 * Get the GitHub OAuth authorization URL from the backend.
 */
export async function getGitHubAuthUrl(): Promise<string> {
  const data = await apiFetch<{ url: string }>("/api/auth/github/url");
  return data.url;
}

/**
 * Exchange a GitHub OAuth code for an access token and user profile.
 */
export async function exchangeGitHubCode(code: string): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/api/auth/github/callback", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

// ========================
// Profile
// ========================

/**
 * Analyze a GitHub user's profile to extract skills and experience.
 */
export async function analyzeProfile(
  username: string,
  token: string,
  signal?: AbortSignal,
): Promise<ProfileAnalysis> {
  return apiFetch<ProfileAnalysis>(
    "/api/profile/analyze",
    {
      method: "POST",
      body: JSON.stringify({ username }),
      signal,
    },
    token,
  );
}

// ========================
// Repositories
// ========================

/**
 * Get recommended repositories based on profile analysis.
 */
export async function getRecommendedRepos(
  params: {
    languages: string[];
    frameworks: string[];
    experience_level: string;
    domains: string[];
  },
  token: string,
  signal?: AbortSignal,
): Promise<RepoRecommendationResponse> {
  return apiFetch<RepoRecommendationResponse>(
    "/api/repos/recommend",
    {
      method: "POST",
      body: JSON.stringify(params),
      signal,
    },
    token,
  );
}

// ========================
// Issues
// ========================

/**
 * Discover beginner-friendly issues matching the user's skills.
 */
export async function discoverIssues(
  params: {
    repositories: string[];
    languages: string[];
    experience_level: string;
  },
  token: string,
  signal?: AbortSignal,
): Promise<IssueDiscoveryResponse> {
  return apiFetch<IssueDiscoveryResponse>(
    "/api/issues/discover",
    {
      method: "POST",
      body: JSON.stringify(params),
      signal,
    },
    token,
  );
}

/**
 * Get an AI-generated explanation for a specific GitHub issue.
 */
export async function explainIssue(
  owner: string,
  repo: string,
  issueNumber: number,
  token: string,
  signal?: AbortSignal,
): Promise<IssueExplanation> {
  return apiFetch<IssueExplanation>(
    "/api/issues/explain",
    {
      method: "POST",
      body: JSON.stringify({
        owner,
        repo,
        issue_number: issueNumber,
      }),
      signal,
    },
    token,
  );
}

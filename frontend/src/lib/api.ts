import type {
  IssueDiscoveryResponse,
  IssueExplanation,
  ProfileAnalysis,
  RepoRecommendationResponse,
} from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

type ApiRequestOptions = {
  token?: string;
  body?: unknown;
};

type RepoRecommendationRequest = {
  languages: string[];
  frameworks: string[];
  experience_level: ProfileAnalysis["experience_level"];
  domains: string[];
};

type IssueDiscoveryRequest = {
  repositories: string[];
  languages: string[];
  experience_level: ProfileAnalysis["experience_level"];
};

async function readError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    // Fall through to status text when the backend did not send JSON.
  }

  return response.statusText || "Request failed";
}

async function postJson<TResponse>(
  path: string,
  { token, body }: ApiRequestOptions = {},
): Promise<TResponse> {
  const headers = new Headers({ "Content-Type": "application/json" });
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body ?? {}),
  });

  if (!response.ok) {
    const message = await readError(response);
    throw new Error(`API error ${response.status}: ${message}`);
  }

  return (await response.json()) as TResponse;
}

export function analyzeProfile(username: string, token: string): Promise<ProfileAnalysis> {
  return postJson<ProfileAnalysis>("/api/profile/analyze", {
    token,
    body: { username },
  });
}

export function getRecommendedRepos(
  request: RepoRecommendationRequest,
  token: string,
): Promise<RepoRecommendationResponse> {
  return postJson<RepoRecommendationResponse>("/api/repos/recommend", {
    token,
    body: request,
  });
}

export function discoverIssues(
  request: IssueDiscoveryRequest,
  token: string,
): Promise<IssueDiscoveryResponse> {
  return postJson<IssueDiscoveryResponse>("/api/issues/discover", {
    token,
    body: request,
  });
}

export function explainIssue(
  owner: string,
  repo: string,
  issueNumber: number,
  token: string,
): Promise<IssueExplanation> {
  return postJson<IssueExplanation>("/api/issues/explain", {
    token,
    body: {
      owner,
      repo,
      issue_number: issueNumber,
    },
  });
}

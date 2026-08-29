"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/shared/navbar";
import { Footer } from "@/components/shared/footer";
import { ProfileCard } from "@/components/dashboard/profile-card";
import { SkillBadges } from "@/components/dashboard/skill-badges";
import { RepoRecommendations } from "@/components/dashboard/repo-recommendations";
import { IssueList } from "@/components/dashboard/issue-list";
import { Button } from "@/components/ui/button";
import { Bot, Loader2 } from "lucide-react";
import { analyzeProfile, getRecommendedRepos, discoverIssues } from "@/lib/api";
import type {
  UserProfile,
  ProfileAnalysis,
  RecommendedRepo,
  DiscoveredIssue,
} from "@/types";

type AgentStep = "idle" | "profile" | "repos" | "issues" | "done" | "error";

// Issue discovery only ever sees repos from this list, so widening it from the
// original 5 spreads recommended issues across more repositories rather than
// clustering on the handful with the highest match score.
const MAX_REPOS_FOR_ISSUE_DISCOVERY = 10;

const AGENT_LABELS: Record<AgentStep, string> = {
  idle: "Waiting...",
  profile: "🔍 Analyzing your GitHub profile...",
  repos: "📦 Finding matching repositories...",
  issues: "🎯 Discovering beginner-friendly issues...",
  done: "✅ Analysis complete!",
  error: "❌ Something went wrong",
};

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  // The analyzed username (once profile analysis completes) can differ from the
  // session's GitHub login normalization; tracked separately so it can override the
  // session-derived profile without re-introducing a setState-in-effect.
  const [analyzedUsername, setAnalyzedUsername] = useState<string | null>(null);
  const [profileAnalysis, setProfileAnalysis] = useState<ProfileAnalysis | null>(null);
  const [repos, setRepos] = useState<RecommendedRepo[]>([]);
  const [issues, setIssues] = useState<DiscoveredIssue[]>([]);
  const [agentStep, setAgentStep] = useState<AgentStep>("idle");
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState(0);

  // Guards the StrictMode double-invoke of this effect in dev, which would otherwise
  // fire the whole (LLM-backed) pipeline twice per mount.
  const runningRef = useRef(false);

  const retry = () => {
    setError(null);
    setAgentStep("idle");
    setRepos([]);
    setIssues([]);
    setRunId((value) => value + 1);
  };

  // Redirect if not authenticated
  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/");
    }
  }, [status, router]);

  // Derived directly from session data on each render — no effect needed, since
  // there's nothing here to synchronize against an external system.
  const userProfile: UserProfile | null = useMemo(() => {
    if (!session?.user) return null;
    const username = analyzedUsername ?? session.username ?? session.user.name ?? "";
    return {
      username,
      name: session.user.name ?? "",
      avatar_url: session.user.image ?? "",
      bio: "",
      public_repos: 0,
      followers: 0,
      following: 0,
      html_url: `https://github.com/${username}`,
      company: null,
      location: null,
      blog: null,
    };
  }, [session, analyzedUsername]);

  // Run the agent pipeline when session is ready.
  //
  // Deliberately excludes `agentStep` from the dependency array even though it's
  // read below: the pipeline calls setAgentStep() repeatedly as it progresses, and
  // if `agentStep` were a dependency, each of those calls would re-trigger this
  // effect, run the AbortController cleanup, and abort the very fetch the step
  // change was reporting progress on — freezing the UI on the first step forever.
  // This effect should only (re-)start the pipeline when the session becomes ready
  // or `retry()` bumps `runId`; `agentStep`'s value is read once at that moment via
  // closure, not tracked as a re-run trigger.
  useEffect(() => {
    if (!session?.accessToken || !session?.username) return;
    if (agentStep !== "idle" || runningRef.current) return;

    runningRef.current = true;
    const controller = new AbortController();

    const runPipeline = async () => {
      const token = session.accessToken;
      const username = session.username;

      try {
        // Step 1: Analyze profile
        setAgentStep("profile");
        const analysis = await analyzeProfile(username, token, controller.signal);
        setProfileAnalysis(analysis);

        // Prefer the analyzed username, once available, over the session-derived one.
        if (analysis.username) {
          setAnalyzedUsername(analysis.username);
        }

        // Step 2: Get repo recommendations
        setAgentStep("repos");
        const repoResponse = await getRecommendedRepos(
          {
            languages: analysis.languages,
            frameworks: analysis.frameworks,
            experience_level: analysis.experience_level,
            domains: analysis.domains,
          },
          token,
          controller.signal,
        );
        setRepos(repoResponse.repositories);

        // Step 3: Discover issues
        setAgentStep("issues");
        const repoNames = repoResponse.repositories
          .slice(0, MAX_REPOS_FOR_ISSUE_DISCOVERY)
          .map((r) => r.full_name);

        if (repoNames.length > 0) {
          const issueResponse = await discoverIssues(
            {
              repositories: repoNames,
              languages: analysis.languages,
              experience_level: analysis.experience_level,
            },
            token,
            controller.signal,
          );
          setIssues(issueResponse.issues);
        }

        setAgentStep("done");
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        console.error("Agent pipeline error:", err);
        setError(err instanceof Error ? err.message : "An unexpected error occurred");
        setAgentStep("error");
      } finally {
        runningRef.current = false;
      }
    };

    runPipeline();

    return () => {
      controller.abort();
      runningRef.current = false;
    };
  }, [session, agentStep, runId]);

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const isProfileError = agentStep === "error" && !profileAnalysis;
  const isReposError = agentStep === "error" && repos.length === 0;
  const isIssuesError = agentStep === "error" && issues.length === 0;

  return (
    <>
      <Navbar />
      <main className="flex-1 pt-20 pb-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          {/* Page header */}
          <div className="mb-8">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
              Your <span className="gradient-text">Dashboard</span>
            </h1>
            <p className="text-muted-foreground mt-1">
              AI-powered insights for your open source journey
            </p>
          </div>

          {/* Agent status bar */}
          {agentStep !== "done" && agentStep !== "idle" && (
            <div
              className={`mb-6 p-3 rounded-lg border flex items-center gap-3 ${
                agentStep === "error"
                  ? "border-destructive/20 bg-destructive/5"
                  : "border-primary/20 bg-primary/5"
              }`}
            >
              {agentStep === "error" ? (
                <>
                  <span className="text-sm text-destructive flex-1">{error}</span>
                  <Button variant="outline" size="sm" onClick={retry} className="shrink-0">
                    Try again
                  </Button>
                </>
              ) : (
                <>
                  <Bot className="h-5 w-5 text-primary animate-pulse" />
                  <span className="text-sm text-primary font-medium">
                    {AGENT_LABELS[agentStep]}
                  </span>
                  <Loader2 className="h-4 w-4 animate-spin text-primary ml-auto" />
                </>
              )}
            </div>
          )}

          {/* Dashboard grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left column — Profile + Skills */}
            <div className="space-y-6">
              <ProfileCard
                user={userProfile}
                isLoading={!userProfile}
              />
              <SkillBadges
                analysis={profileAnalysis}
                isLoading={agentStep === "profile" || agentStep === "idle"}
                isError={isProfileError}
              />
            </div>

            {/* Right column — Repos + Issues */}
            <div className="lg:col-span-2 space-y-6">
              <RepoRecommendations
                repos={repos}
                isLoading={agentStep === "profile" || agentStep === "repos" || agentStep === "idle"}
                isError={isReposError}
              />
              <IssueList
                issues={issues}
                isLoading={
                  agentStep === "profile" ||
                  agentStep === "repos" ||
                  agentStep === "issues" ||
                  agentStep === "idle"
                }
                isError={isIssuesError}
              />
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}

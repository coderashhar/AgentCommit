"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/shared/navbar";
import { Footer } from "@/components/shared/footer";
import { ProfileCard } from "@/components/dashboard/profile-card";
import { SkillBadges } from "@/components/dashboard/skill-badges";
import { RepoRecommendations } from "@/components/dashboard/repo-recommendations";
import { IssueList } from "@/components/dashboard/issue-list";
import { Badge } from "@/components/ui/badge";
import { Bot, Loader2 } from "lucide-react";
import { analyzeProfile, getRecommendedRepos, discoverIssues } from "@/lib/api";
import type {
  UserProfile,
  ProfileAnalysis,
  RecommendedRepo,
  DiscoveredIssue,
} from "@/types";

type AgentStep = "idle" | "profile" | "repos" | "issues" | "done" | "error";

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [profileAnalysis, setProfileAnalysis] = useState<ProfileAnalysis | null>(null);
  const [repos, setRepos] = useState<RecommendedRepo[]>([]);
  const [issues, setIssues] = useState<DiscoveredIssue[]>([]);
  const [agentStep, setAgentStep] = useState<AgentStep>("idle");
  const [error, setError] = useState<string | null>(null);

  // Redirect if not authenticated
  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/");
    }
  }, [status, router]);

  // Build user profile from session data
  useEffect(() => {
    if (session?.user) {
      setUserProfile({
        username: session.username ?? session.user.name ?? "",
        name: session.user.name ?? "",
        avatar_url: session.user.image ?? "",
        bio: "",
        public_repos: 0,
        followers: 0,
        following: 0,
        html_url: `https://github.com/${session.username ?? session.user.name}`,
        company: null,
        location: null,
        blog: null,
      });
    }
  }, [session]);

  // Run the agent pipeline when session is ready
  useEffect(() => {
    if (!session?.accessToken || !session?.username || agentStep !== "idle") return;

    const runPipeline = async () => {
      const token = session.accessToken;
      const username = session.username;

      try {
        // Step 1: Analyze profile
        setAgentStep("profile");
        const analysis = await analyzeProfile(username, token);
        setProfileAnalysis(analysis);

        // Update user profile with enriched data from analysis
        setUserProfile((prev) =>
          prev ? { ...prev, username: analysis.username || prev.username } : prev,
        );

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
        );
        setRepos(repoResponse.repositories);

        // Step 3: Discover issues
        setAgentStep("issues");
        const repoNames = repoResponse.repositories
          .slice(0, 5)
          .map((r) => r.full_name);

        if (repoNames.length > 0) {
          const issueResponse = await discoverIssues(
            {
              repositories: repoNames,
              languages: analysis.languages,
              experience_level: analysis.experience_level,
            },
            token,
          );
          setIssues(issueResponse.issues);
        }

        setAgentStep("done");
      } catch (err) {
        console.error("Agent pipeline error:", err);
        setError(err instanceof Error ? err.message : "An unexpected error occurred");
        setAgentStep("error");
      }
    };

    runPipeline();
  }, [session, agentStep]);

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const agentLabels: Record<AgentStep, string> = {
    idle: "Waiting...",
    profile: "🔍 Analyzing your GitHub profile...",
    repos: "📦 Finding matching repositories...",
    issues: "🎯 Discovering beginner-friendly issues...",
    done: "✅ Analysis complete!",
    error: "❌ Something went wrong",
  };

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
            <div className="mb-6 p-3 rounded-lg border border-primary/20 bg-primary/5 flex items-center gap-3">
              {agentStep === "error" ? (
                <span className="text-sm text-destructive">{error}</span>
              ) : (
                <>
                  <Bot className="h-5 w-5 text-primary animate-pulse" />
                  <span className="text-sm text-primary font-medium">
                    {agentLabels[agentStep]}
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
              />
            </div>

            {/* Right column — Repos + Issues */}
            <div className="lg:col-span-2 space-y-6">
              <RepoRecommendations
                repos={repos}
                isLoading={agentStep === "profile" || agentStep === "repos" || agentStep === "idle"}
              />
              <IssueList
                issues={issues}
                isLoading={
                  agentStep === "profile" ||
                  agentStep === "repos" ||
                  agentStep === "issues" ||
                  agentStep === "idle"
                }
              />
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}

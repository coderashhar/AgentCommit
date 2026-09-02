"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Navbar } from "@/components/shared/navbar";
import { Footer } from "@/components/shared/footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ArrowLeft,
  Bot,
  BookOpen,
  ChevronDown,
  ChevronRight,
  Clock,
  FileCode,
  ExternalLink,
  GitCommit,
  Lightbulb,
  Loader2,
  MapPin,
  MessageCircle,
  Star,
  TriangleAlert,
  Zap,
} from "lucide-react";
import { explainIssue, getImplementationPlan, sendMentorMessage } from "@/lib/api";
import { ChatPanel } from "@/components/mentor/chat-panel";
import type { IssueExplanation, ImplementationPlan } from "@/types";

export default function IssueDetailPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const params = useParams();

  const [explanation, setExplanation] = useState<IssueExplanation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [plan, setPlan] = useState<ImplementationPlan | null>(null);
  const [isPlanLoading, setIsPlanLoading] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);
  const [planExpanded, setPlanExpanded] = useState(false);

  const [mentorOpen, setMentorOpen] = useState(false);

  // Extract owner/repo and issue number from URL params
  const segments = params.id as string[] | undefined;
  const owner = segments?.[0] ?? "";
  const repo = segments?.[1] ?? "";
  const parsedIssueNumber = Number.parseInt(segments?.[2] ?? "", 10);
  const issueNumber = Number.isFinite(parsedIssueNumber) ? parsedIssueNumber : 0;
  const hasValidParams = Boolean(owner) && Boolean(repo) && issueNumber > 0;

  const [retryToken, setRetryToken] = useState(0);
  const retry = () => {
    setError(null);
    setRetryToken((value) => value + 1);
  };

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/");
      return;
    }

    // Malformed URL (e.g. a stray link or a manually-edited address): the render
    // below returns the "not found" page before ever consulting `isLoading`, so
    // there's nothing to synchronize here — just skip starting a fetch that would
    // never resolve to anything valid.
    if (!hasValidParams) return;

    if (!session?.accessToken) return;

    let cancelled = false;
    const controller = new AbortController();

    const fetchExplanation = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const result = await explainIssue(owner, repo, issueNumber, session.accessToken, controller.signal);
        if (!cancelled) setExplanation(result);
      } catch (err) {
        if (cancelled || (err instanceof DOMException && err.name === "AbortError")) return;
        console.error("Issue explanation error:", err);
        setError(err instanceof Error ? err.message : "Failed to explain issue");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    fetchExplanation();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [session, status, owner, repo, issueNumber, hasValidParams, router, retryToken]);

  const fetchPlan = async () => {
    if (!session?.accessToken || !hasValidParams) return;
    setIsPlanLoading(true);
    setPlanError(null);
    setPlanExpanded(true);
    try {
      const result = await getImplementationPlan(owner, repo, issueNumber, session.accessToken);
      setPlan(result);
    } catch (err) {
      setPlanError(err instanceof Error ? err.message : "Failed to generate plan");
    } finally {
      setIsPlanLoading(false);
    }
  };

  const handleMentorSend = async (message: string): Promise<string> => {
    if (!session?.accessToken) throw new Error("Not authenticated");
    const result = await sendMentorMessage(owner, repo, issueNumber, message, session.accessToken);
    return result.response;
  };

  const complexityColor = {
    low: "text-emerald-500",
    medium: "text-amber-500",
    high: "text-rose-500",
  };

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const difficultyStars = (level: number) =>
    Array.from({ length: 5 }, (_, i) => (
      <Star
        key={i}
        className={`h-4 w-4 ${i < level ? "text-amber-400 fill-amber-400" : "text-muted-foreground/30"}`}
      />
    ));

  if (!hasValidParams) {
    return (
      <>
        <Navbar />
        <main className="flex-1 pt-20 pb-12">
          <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center py-16">
            <h1 className="text-2xl font-bold tracking-tight mb-2">Issue not found</h1>
            <p className="text-sm text-muted-foreground mb-6">
              This link doesn&apos;t point to a valid issue.
            </p>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Dashboard
            </Link>
          </div>
        </main>
        <Footer />
      </>
    );
  }

  return (
    <>
      <Navbar />
      <main className="flex-1 pt-20 pb-12">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          {/* Back button */}
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-6"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>

          {/* Issue header */}
          <div className="mb-6">
            <p className="text-sm text-muted-foreground mb-1">
              {owner}/{repo} #{issueNumber}
            </p>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
              {isLoading ? <Skeleton className="h-8 w-96" /> : explanation?.title}
            </h1>
          </div>

          {/* Agent thinking indicator */}
          {isLoading && (
            <div className="mb-6 p-4 rounded-lg border border-primary/20 bg-primary/5 flex items-center gap-3">
              <Bot className="h-5 w-5 text-primary animate-pulse" />
              <span className="text-sm text-primary font-medium">
                AI is analyzing this issue...
              </span>
              <Loader2 className="h-4 w-4 animate-spin text-primary ml-auto" />
            </div>
          )}

          {error && (
            <div className="mb-6 p-4 rounded-lg border border-destructive/20 bg-destructive/5 flex items-center justify-between gap-4">
              <p className="text-sm text-destructive">{error}</p>
              <Button variant="outline" size="sm" onClick={retry} className="shrink-0">
                Try again
              </Button>
            </div>
          )}

          {/* Implementation Plan Section */}
          {explanation && (
            <div className="mb-6">
              {!plan && !isPlanLoading && (
                <div className="flex flex-wrap gap-3">
                  <Button
                    onClick={fetchPlan}
                    variant="outline"
                    className="gap-2"
                    disabled={isPlanLoading}
                  >
                    <Zap className="h-4 w-4 text-primary" />
                    Generate Implementation Plan
                  </Button>
                  <Link
                    href={`/commit?repo=${encodeURIComponent(`${owner}/${repo}`)}&issue_number=${issueNumber}&issue_title=${encodeURIComponent(explanation?.title ?? "")}`}
                    className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground transition-colors"
                  >
                    <GitCommit className="h-4 w-4 text-primary" />
                    Generate Commit Message
                  </Link>
                </div>
              )}

              {isPlanLoading && (
                <div className="p-4 rounded-lg border border-primary/20 bg-primary/5 flex items-center gap-3">
                  <MapPin className="h-5 w-5 text-primary animate-pulse" />
                  <span className="text-sm text-primary font-medium">
                    AI is generating an implementation plan...
                  </span>
                  <Loader2 className="h-4 w-4 animate-spin text-primary ml-auto" />
                </div>
              )}

              {planError && (
                <div className="p-4 rounded-lg border border-destructive/20 bg-destructive/5 flex items-center justify-between gap-4">
                  <p className="text-sm text-destructive">{planError}</p>
                  <Button variant="outline" size="sm" onClick={fetchPlan} className="shrink-0">
                    Try again
                  </Button>
                </div>
              )}

              {plan && (
                <div className="rounded-lg border border-border/50 overflow-hidden">
                  {/* Plan header / toggle */}
                  <button
                    onClick={() => setPlanExpanded((v) => !v)}
                    className="w-full flex items-center justify-between p-4 bg-muted/30 hover:bg-muted/50 transition-colors text-left"
                  >
                    <div className="flex items-center gap-3">
                      <MapPin className="h-5 w-5 text-primary" />
                      <div>
                        <p className="font-semibold text-sm">{plan.title}</p>
                        <p className="text-xs text-muted-foreground capitalize">
                          Complexity:{" "}
                          <span className={complexityColor[plan.estimated_complexity] ?? "text-foreground"}>
                            {plan.estimated_complexity}
                          </span>
                          {plan.steps.length > 0 && ` · ${plan.steps.length} steps`}
                        </p>
                      </div>
                    </div>
                    {planExpanded ? (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    )}
                  </button>

                  {planExpanded && (
                    <div className="p-4 space-y-6">
                      {/* Issue summary */}
                      {plan.issue_summary && (
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          {plan.issue_summary}
                        </p>
                      )}

                      {/* Steps */}
                      {plan.steps.length > 0 && (
                        <div className="space-y-4">
                          {plan.steps.map((step) => (
                            <div
                              key={step.step_number}
                              className="flex gap-3"
                            >
                              <div className="flex-none w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center mt-0.5">
                                {step.step_number}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-sm mb-1">{step.title}</p>
                                <p className="text-sm text-muted-foreground leading-relaxed">
                                  {step.description}
                                </p>
                                {step.files_to_modify.length > 0 && (
                                  <div className="mt-2 flex flex-wrap gap-1.5">
                                    {step.files_to_modify.map((file, i) => (
                                      <span
                                        key={`${file}-${i}`}
                                        className="text-xs font-mono bg-muted/60 rounded px-1.5 py-0.5 text-muted-foreground"
                                      >
                                        {file}
                                      </span>
                                    ))}
                                  </div>
                                )}
                                {step.code_hints && (
                                  <p className="mt-2 text-xs text-muted-foreground italic">
                                    Hint: {step.code_hints}
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Prerequisite knowledge */}
                      {plan.prerequisite_knowledge.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                            Prerequisite Knowledge
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {plan.prerequisite_knowledge.map((item, i) => (
                              <Badge key={`${item}-${i}`} variant="secondary" className="text-xs">
                                {item}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Risks & Edge Cases */}
                      {(plan.risks.length > 0 || plan.edge_cases.length > 0) && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          {plan.risks.length > 0 && (
                            <div>
                              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1">
                                <TriangleAlert className="h-3 w-3" /> Risks
                              </p>
                              <ul className="space-y-1">
                                {plan.risks.map((risk, i) => (
                                  <li key={i} className="text-xs text-muted-foreground">
                                    · {risk}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {plan.edge_cases.length > 0 && (
                            <div>
                              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                                Edge Cases
                              </p>
                              <ul className="space-y-1">
                                {plan.edge_cases.map((ec, i) => (
                                  <li key={i} className="text-xs text-muted-foreground">
                                    · {ec}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Testing strategy */}
                      {plan.testing_strategy && (
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                            Testing Strategy
                          </p>
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            {plan.testing_strategy}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Mentor Chat Section */}
          {explanation && (
            <div className="mb-6">
              <div className="rounded-lg border border-border/50 overflow-hidden">
                <button
                  onClick={() => setMentorOpen((v) => !v)}
                  className="w-full flex items-center justify-between p-4 bg-muted/30 hover:bg-muted/50 transition-colors text-left"
                >
                  <div className="flex items-center gap-3">
                    <MessageCircle className="h-5 w-5 text-primary" />
                    <div>
                      <p className="font-semibold text-sm">Ask the Mentor</p>
                      <p className="text-xs text-muted-foreground">
                        Conversational guidance — I&apos;ll guide you, not solve it for you
                      </p>
                    </div>
                  </div>
                  {mentorOpen ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                </button>

                {mentorOpen && (
                  <div className="h-96">
                    <ChatPanel
                      owner={owner}
                      repo={repo}
                      issueNumber={issueNumber}
                      token={session?.accessToken ?? ""}
                      onSendMessage={handleMentorSend}
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          {explanation && (
            <div className="space-y-6">
              {/* Quick stats row */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card className="border-border/50">
                  <CardContent className="p-4 flex items-center gap-3">
                    <div className="flex">{difficultyStars(explanation.difficulty)}</div>
                    <span className="text-sm text-muted-foreground">Difficulty</span>
                  </CardContent>
                </Card>
                <Card className="border-border/50">
                  <CardContent className="p-4 flex items-center gap-3">
                    <Clock className="h-5 w-5 text-primary" />
                    <span className="text-sm font-medium">{explanation.estimated_time}</span>
                    <span className="text-sm text-muted-foreground">Estimated</span>
                  </CardContent>
                </Card>
                <Card className="border-border/50">
                  <CardContent className="p-4">
                    <a
                      href={`https://github.com/${owner}/${repo}/issues/${issueNumber}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-sm text-primary hover:underline"
                    >
                      <ExternalLink className="h-4 w-4" />
                      View on GitHub
                    </a>
                  </CardContent>
                </Card>
              </div>

              {/* AI Explanation */}
              <Card className="border-border/50">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Bot className="h-5 w-5 text-primary" />
                    AI Explanation
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">
                    {explanation.summary}
                  </p>
                </CardContent>
              </Card>

              {/* Required Concepts */}
              {explanation.required_concepts.length > 0 && (
                <Card className="border-border/50">
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Lightbulb className="h-5 w-5 text-amber-500" />
                      Concepts You&apos;ll Need
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {explanation.required_concepts.map((concept, index) => (
                        <Badge key={`${concept}-${index}`} variant="secondary" className="text-sm">
                          {concept}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Suggested Approach */}
              {explanation.suggested_approach && (
                <Card className="border-border/50">
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <BookOpen className="h-5 w-5 text-emerald-500" />
                      Suggested Approach
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">
                      {explanation.suggested_approach}
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* Files to Explore + Resources side by side */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                {explanation.files_to_explore.length > 0 && (
                  <Card className="border-border/50">
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <FileCode className="h-4 w-4 text-violet-500" />
                        Files to Explore
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-1.5">
                        {explanation.files_to_explore.map((file, index) => (
                          <li
                            key={`${file}-${index}`}
                            className="text-sm text-muted-foreground font-mono bg-muted/50 rounded px-2 py-1"
                          >
                            {file}
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                )}

                {explanation.learning_resources.length > 0 && (
                  <Card className="border-border/50">
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <BookOpen className="h-4 w-4 text-cyan-500" />
                        Learning Resources
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-1.5">
                        {explanation.learning_resources.map((resource, index) => (
                          <li key={`${resource}-${index}`} className="text-sm">
                            {resource.startsWith("http") ? (
                              <a
                                href={resource}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary hover:underline truncate block"
                              >
                                {resource}
                              </a>
                            ) : (
                              <span className="text-muted-foreground">{resource}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
      <Footer />
    </>
  );
}

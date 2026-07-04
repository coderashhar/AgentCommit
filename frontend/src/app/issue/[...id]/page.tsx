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
import { Separator } from "@/components/ui/separator";
import {
  ArrowLeft,
  Bot,
  BookOpen,
  Clock,
  FileCode,
  ExternalLink,
  Lightbulb,
  Loader2,
  Star,
} from "lucide-react";
import { explainIssue } from "@/lib/api";
import type { IssueExplanation } from "@/types";

export default function IssueDetailPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const params = useParams();

  const [explanation, setExplanation] = useState<IssueExplanation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Extract owner/repo and issue number from URL params
  const segments = params.id as string[];
  const owner = segments?.[0] ?? "";
  const repo = segments?.[1] ?? "";
  const issueNumber = parseInt(segments?.[2] ?? "0", 10);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/");
      return;
    }

    if (!session?.accessToken || !owner || !repo || !issueNumber) return;

    const fetchExplanation = async () => {
      try {
        setIsLoading(true);
        const result = await explainIssue(owner, repo, issueNumber, session.accessToken);
        setExplanation(result);
      } catch (err) {
        console.error("Issue explanation error:", err);
        setError(err instanceof Error ? err.message : "Failed to explain issue");
      } finally {
        setIsLoading(false);
      }
    };

    fetchExplanation();
  }, [session, status, owner, repo, issueNumber, router]);

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
            <div className="mb-6 p-4 rounded-lg border border-destructive/20 bg-destructive/5">
              <p className="text-sm text-destructive">{error}</p>
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
                      {explanation.required_concepts.map((concept) => (
                        <Badge key={concept} variant="secondary" className="text-sm">
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
                        {explanation.files_to_explore.map((file) => (
                          <li
                            key={file}
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
                        {explanation.learning_resources.map((resource) => (
                          <li key={resource} className="text-sm">
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

"use client";

import { useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { MessageSquare, ArrowRight, Bookmark, BookmarkCheck } from "lucide-react";
import { timeAgo, difficultyToStars } from "@/lib/utils";
import { saveIssue, unsaveIssue } from "@/lib/api";
import type { DiscoveredIssue } from "@/types";

interface IssueListProps {
  issues: DiscoveredIssue[];
  isLoading: boolean;
  isError?: boolean;
}

const difficultyColors: Record<string, string> = {
  easy: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  medium: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  hard: "bg-red-500/10 text-red-500 border-red-500/20",
};

export function IssueList({ issues, isLoading, isError = false }: IssueListProps) {
  const { data: session } = useSession();
  const [savedKeys, setSavedKeys] = useState<Set<string>>(new Set());
  const [savingKeys, setSavingKeys] = useState<Set<string>>(new Set());

  const issueKey = (issue: DiscoveredIssue) => `${issue.repo_full_name}#${issue.number}`;

  const toggleSave = async (e: React.MouseEvent, issue: DiscoveredIssue) => {
    e.preventDefault(); // prevent navigating to issue detail
    const token = session?.accessToken;
    if (!token) return;

    const key = issueKey(issue);
    setSavingKeys((prev) => new Set(prev).add(key));

    try {
      if (savedKeys.has(key)) {
        const [owner, repo] = issue.repo_full_name.split("/");
        await unsaveIssue(owner, repo, issue.number, token);
        setSavedKeys((prev) => { const next = new Set(prev); next.delete(key); return next; });
      } else {
        await saveIssue(
          { repo_full_name: issue.repo_full_name, issue_number: issue.number, title: issue.title, html_url: issue.html_url },
          token,
        );
        setSavedKeys((prev) => new Set(prev).add(key));
      }
    } catch {
      // fail silently — saving is non-critical
    } finally {
      setSavingKeys((prev) => { const next = new Set(prev); next.delete(key); return next; });
    }
  };
  if (isLoading) {
    return (
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-lg">Recommended Issues</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="p-4 rounded-lg border border-border/50 space-y-2">
              <Skeleton className="h-5 w-64" />
              <Skeleton className="h-4 w-40" />
              <div className="flex gap-2">
                <Skeleton className="h-5 w-20 rounded-full" />
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-lg">Recommended Issues</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-8">
            Couldn&apos;t load issue recommendations.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (issues.length === 0) {
    return (
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-lg">Recommended Issues</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-8">
            No matching issues found yet.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="text-lg">Recommended Issues</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {issues.map((issue) => (
          <Link
            key={`${issue.repo_full_name}#${issue.number}`}
            href={`/issue/${issue.repo_full_name}/${issue.number}`}
            className="block p-4 rounded-lg border border-border/50 hover:border-primary/30 hover:bg-muted/50 transition-all group"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <h4 className="text-sm font-semibold group-hover:text-primary transition-colors line-clamp-1">
                  {issue.title}
                </h4>
                <p className="text-xs text-muted-foreground mt-1">
                  {issue.repo_full_name} #{issue.number}
                </p>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={(e) => toggleSave(e, issue)}
                  disabled={savingKeys.has(issueKey(issue))}
                  aria-label={savedKeys.has(issueKey(issue)) ? "Unsave issue" : "Save issue"}
                >
                  {savedKeys.has(issueKey(issue))
                    ? <BookmarkCheck className="h-4 w-4 text-primary" />
                    : <Bookmark className="h-4 w-4" />}
                </Button>
                <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>

            {issue.body_preview && (
              <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                {issue.body_preview}
              </p>
            )}

            <div className="flex items-center gap-2 mt-3 flex-wrap">
              <Badge
                variant="outline"
                className={`text-xs ${difficultyColors[issue.difficulty] || difficultyColors.easy}`}
              >
                {difficultyToStars(issue.difficulty)} {issue.difficulty}
              </Badge>

              {issue.labels.slice(0, 3).map((label) => (
                <Badge key={label} variant="secondary" className="text-xs">
                  {label}
                </Badge>
              ))}

              <div className="flex items-center gap-3 ml-auto text-xs text-muted-foreground">
                {issue.comments > 0 && (
                  <span className="flex items-center gap-1">
                    <MessageSquare className="h-3 w-3" />
                    {issue.comments}
                  </span>
                )}
                {issue.created_at && (
                  <span>{timeAgo(issue.created_at)}</span>
                )}
              </div>
            </div>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}

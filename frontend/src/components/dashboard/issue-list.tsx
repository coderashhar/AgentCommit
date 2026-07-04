"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageSquare, ArrowRight } from "lucide-react";
import { timeAgo, difficultyToStars } from "@/lib/utils";
import type { DiscoveredIssue } from "@/types";

interface IssueListProps {
  issues: DiscoveredIssue[];
  isLoading: boolean;
}

const difficultyColors: Record<string, string> = {
  easy: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  medium: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  hard: "bg-red-500/10 text-red-500 border-red-500/20",
};

function issueDetailHref(issue: DiscoveredIssue): string {
  const [owner, repo] = issue.repo_full_name.split("/");
  if (!owner || !repo) {
    return issue.html_url || "#";
  }

  return `/issue/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/${issue.number}`;
}

export function IssueList({ issues, isLoading }: IssueListProps) {
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

  if (issues.length === 0) {
    return (
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-lg">Recommended Issues</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-8">
            Finding beginner-friendly issues for you...
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
            href={issueDetailHref(issue)}
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
              <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
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

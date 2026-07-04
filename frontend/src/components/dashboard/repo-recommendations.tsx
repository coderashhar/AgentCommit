"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Star, GitFork, ExternalLink } from "lucide-react";
import { formatNumber } from "@/lib/utils";
import type { RecommendedRepo } from "@/types";

interface RepoRecommendationsProps {
  repos: RecommendedRepo[];
  isLoading: boolean;
}

export function RepoRecommendations({ repos, isLoading }: RepoRecommendationsProps) {
  if (isLoading) {
    return (
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-lg">Recommended Repositories</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="p-4 rounded-lg border border-border/50 space-y-2">
              <Skeleton className="h-5 w-48" />
              <Skeleton className="h-4 w-full" />
              <div className="flex gap-2">
                <Skeleton className="h-5 w-16 rounded-full" />
                <Skeleton className="h-5 w-12 rounded-full" />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (repos.length === 0) {
    return (
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-lg">Recommended Repositories</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-8">
            Analyzing your profile to find matching repositories...
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="text-lg">Recommended Repositories</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {repos.map((repo) => (
          <a
            key={repo.full_name}
            href={repo.html_url}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-4 rounded-lg border border-border/50 hover:border-primary/30 hover:bg-muted/50 transition-all group"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <h4 className="text-sm font-semibold group-hover:text-primary transition-colors truncate">
                  {repo.full_name}
                </h4>
                {repo.description && (
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                    {repo.description}
                  </p>
                )}
              </div>
              <ExternalLink className="h-3.5 w-3.5 text-muted-foreground shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>

            <div className="flex items-center gap-3 mt-3">
              {repo.language && (
                <Badge variant="secondary" className="text-xs">
                  {repo.language}
                </Badge>
              )}
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Star className="h-3 w-3" />
                {formatNumber(repo.stars)}
              </span>
              {repo.match_score > 0 && (
                <Badge variant="outline" className="text-xs border-primary/20 text-primary ml-auto">
                  {Math.round(repo.match_score)}% match
                </Badge>
              )}
            </div>

            {repo.match_reason && (
              <p className="text-xs text-muted-foreground mt-2 italic">
                &ldquo;{repo.match_reason}&rdquo;
              </p>
            )}
          </a>
        ))}
      </CardContent>
    </Card>
  );
}

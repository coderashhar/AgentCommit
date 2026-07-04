"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Code, Layers, Target, Zap } from "lucide-react";
import type { ProfileAnalysis } from "@/types";

interface SkillBadgesProps {
  analysis: ProfileAnalysis | null;
  isLoading: boolean;
}

const levelColors: Record<string, string> = {
  beginner: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  intermediate: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  advanced: "bg-violet-500/10 text-violet-500 border-violet-500/20",
};

export function SkillBadges({ analysis, isLoading }: SkillBadgesProps) {
  if (isLoading) {
    return (
      <Card className="border-border/50">
        <CardContent className="p-6 space-y-4">
          <Skeleton className="h-5 w-24" />
          <div className="flex flex-wrap gap-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-6 w-16 rounded-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!analysis) return null;

  return (
    <Card className="border-border/50 hover:border-primary/20 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Skills Analysis</CardTitle>
          <Badge
            variant="outline"
            className={levelColors[analysis.experience_level] || levelColors.beginner}
          >
            {analysis.experience_level}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-0 space-y-4">
        {/* Languages */}
        {analysis.languages.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground flex items-center gap-1.5 mb-2">
              <Code className="h-3 w-3" />
              Languages
            </p>
            <div className="flex flex-wrap gap-1.5">
              {analysis.languages.map((lang) => (
                <Badge key={lang} variant="secondary" className="text-xs">
                  {lang}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Frameworks */}
        {analysis.frameworks.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground flex items-center gap-1.5 mb-2">
              <Layers className="h-3 w-3" />
              Frameworks
            </p>
            <div className="flex flex-wrap gap-1.5">
              {analysis.frameworks.map((fw) => (
                <Badge key={fw} variant="outline" className="text-xs">
                  {fw}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Domains */}
        {analysis.domains.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground flex items-center gap-1.5 mb-2">
              <Target className="h-3 w-3" />
              Domains
            </p>
            <div className="flex flex-wrap gap-1.5">
              {analysis.domains.map((domain) => (
                <Badge key={domain} variant="outline" className="text-xs border-primary/20 text-primary">
                  {domain}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Summary */}
        {analysis.summary && (
          <div className="pt-2 border-t border-border/50">
            <p className="text-xs text-muted-foreground flex items-center gap-1.5 mb-1">
              <Zap className="h-3 w-3" />
              AI Summary
            </p>
            <p className="text-sm text-foreground/80 leading-relaxed">{analysis.summary}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

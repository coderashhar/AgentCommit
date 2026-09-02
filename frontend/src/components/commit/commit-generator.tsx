"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Check,
  Clipboard,
  GitCommit,
  Loader2,
  TriangleAlert,
  Zap,
} from "lucide-react";
import { generateCommitMessage } from "@/lib/api";
import type { CommitMessageResponse } from "@/types";

interface CommitGeneratorProps {
  token: string;
  /** Pre-filled from issue context when opened from an issue page */
  initialRepoFullName?: string;
  initialIssueTitle?: string;
  initialIssueNumber?: number;
}

const COMMIT_TYPES = ["feat", "fix", "docs", "style", "refactor", "perf", "test", "chore", "ci", "build"];

const typeColor: Record<string, string> = {
  feat: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
  fix: "bg-rose-500/10 text-rose-600 border-rose-500/20",
  docs: "bg-sky-500/10 text-sky-600 border-sky-500/20",
  style: "bg-violet-500/10 text-violet-600 border-violet-500/20",
  refactor: "bg-amber-500/10 text-amber-600 border-amber-500/20",
  perf: "bg-orange-500/10 text-orange-600 border-orange-500/20",
  test: "bg-cyan-500/10 text-cyan-600 border-cyan-500/20",
  chore: "bg-slate-500/10 text-slate-600 border-slate-500/20",
  ci: "bg-blue-500/10 text-blue-600 border-blue-500/20",
  build: "bg-indigo-500/10 text-indigo-600 border-indigo-500/20",
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button variant="outline" size="sm" onClick={copy} className="gap-1.5 shrink-0">
      {copied ? (
        <>
          <Check className="h-3.5 w-3.5 text-emerald-500" />
          Copied
        </>
      ) : (
        <>
          <Clipboard className="h-3.5 w-3.5" />
          Copy
        </>
      )}
    </Button>
  );
}

export function CommitGenerator({
  token,
  initialRepoFullName = "",
  initialIssueTitle = "",
  initialIssueNumber,
}: CommitGeneratorProps) {
  const [repoFullName, setRepoFullName] = useState(initialRepoFullName);
  const [issueTitle, setIssueTitle] = useState(initialIssueTitle);
  const [issueNumber, setIssueNumber] = useState<string>(
    initialIssueNumber ? String(initialIssueNumber) : "",
  );
  const [changeDescription, setChangeDescription] = useState("");
  const [diffText, setDiffText] = useState("");
  const [result, setResult] = useState<CommitMessageResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canGenerate = Boolean(changeDescription.trim()) && Boolean(repoFullName.trim());

  const handleGenerate = async () => {
    if (!canGenerate) return;
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await generateCommitMessage(
        {
          diff_text: diffText,
          change_description: changeDescription,
          repo_full_name: repoFullName,
          issue_title: issueTitle,
          issue_number: issueNumber ? Number(issueNumber) : undefined,
        },
        token,
      );
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate commit message.");
    } finally {
      setIsLoading(false);
    }
  };

  const typeClass = result ? (typeColor[result.commit_type] ?? typeColor.chore) : "";

  return (
    <div className="space-y-6">
      {/* Inputs */}
      <div className="space-y-4">
        {/* Repository */}
        <div>
          <label className="block text-sm font-medium mb-1.5">
            Repository <span className="text-destructive">*</span>
          </label>
          <input
            type="text"
            value={repoFullName}
            onChange={(e) => setRepoFullName(e.target.value)}
            placeholder="owner/repo"
            className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </div>

        {/* Issue context (optional) */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-2">
            <label className="block text-sm font-medium mb-1.5">
              Issue title <span className="text-muted-foreground text-xs">(optional)</span>
            </label>
            <input
              type="text"
              value={issueTitle}
              onChange={(e) => setIssueTitle(e.target.value)}
              placeholder="e.g. Add retry logic to API client"
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">
              Issue # <span className="text-muted-foreground text-xs">(optional)</span>
            </label>
            <input
              type="number"
              min={1}
              value={issueNumber}
              onChange={(e) => setIssueNumber(e.target.value)}
              placeholder="42"
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
        </div>

        {/* Change description */}
        <div>
          <label className="block text-sm font-medium mb-1.5">
            Change description <span className="text-destructive">*</span>
          </label>
          <textarea
            value={changeDescription}
            onChange={(e) => setChangeDescription(e.target.value)}
            maxLength={2000}
            rows={3}
            placeholder="Describe what you changed and why…"
            className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-none"
          />
        </div>

        {/* Diff (optional, collapsible) */}
        <details className="group">
          <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground transition-colors select-none">
            Paste git diff <span className="text-xs">(optional — improves accuracy)</span>
          </summary>
          <div className="mt-2">
            <textarea
              value={diffText}
              onChange={(e) => setDiffText(e.target.value)}
              maxLength={10000}
              rows={6}
              placeholder="Paste output of `git diff` here…"
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-xs font-mono placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-y"
            />
            <p className="text-xs text-muted-foreground mt-1 text-right">
              {diffText.length}/10 000 chars
            </p>
          </div>
        </details>

        <Button
          onClick={handleGenerate}
          disabled={!canGenerate || isLoading}
          className="gap-2"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Zap className="h-4 w-4" />
          )}
          {isLoading ? "Generating…" : "Generate Commit Message"}
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 rounded-lg border border-destructive/20 bg-destructive/5 flex items-center gap-3">
          <TriangleAlert className="h-4 w-4 text-destructive shrink-0" />
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="space-y-4">
          {/* Type badge + breaking change */}
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${typeClass}`}
            >
              {result.commit_type}
            </span>
            {result.scope && (
              <Badge variant="outline" className="text-xs">
                scope: {result.scope}
              </Badge>
            )}
            {result.breaking_change && (
              <Badge variant="destructive" className="text-xs gap-1">
                <TriangleAlert className="h-3 w-3" />
                BREAKING CHANGE
              </Badge>
            )}
          </div>

          {/* Full commit message */}
          <Card className="border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <GitCommit className="h-4 w-4 text-primary" />
                Commit Message
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-start justify-between gap-3">
                <pre className="flex-1 text-sm font-mono whitespace-pre-wrap break-words bg-muted/40 rounded-lg p-3">
                  {result.full_message}
                </pre>
                <CopyButton text={result.full_message} />
              </div>
            </CardContent>
          </Card>

          {/* Alternatives */}
          {result.alternatives.length > 0 && (
            <Card className="border-border/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">
                  Alternative subject lines
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {result.alternatives.map((alt, i) => (
                    <li key={i} className="flex items-center justify-between gap-3">
                      <code className="flex-1 text-xs font-mono bg-muted/40 rounded px-2 py-1 truncate">
                        {alt}
                      </code>
                      <CopyButton text={alt} />
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

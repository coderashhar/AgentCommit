"use client";

import { useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { Navbar } from "@/components/shared/navbar";
import { Footer } from "@/components/shared/footer";
import { CommitGenerator } from "@/components/commit/commit-generator";
import { GitCommit, Loader2 } from "lucide-react";

export default function CommitPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();

  const repoFullName = searchParams.get("repo") ?? "";
  const issueTitle = searchParams.get("issue_title") ?? "";
  const issueNumberRaw = searchParams.get("issue_number");
  const issueNumber = issueNumberRaw ? Number(issueNumberRaw) : undefined;

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!session?.accessToken) return null;

  return (
    <>
      <Navbar />
      <main className="flex-1 pt-20 pb-12">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <GitCommit className="h-7 w-7 text-primary" />
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
                Commit Message Generator
              </h1>
            </div>
            <p className="text-sm text-muted-foreground">
              Describe your change (and optionally paste a git diff) to get a
              conventional commit message — with alternatives.
            </p>
          </div>

          <CommitGenerator
            token={session.accessToken}
            initialRepoFullName={repoFullName}
            initialIssueTitle={issueTitle}
            initialIssueNumber={issueNumber}
          />
        </div>
      </main>
      <Footer />
    </>
  );
}

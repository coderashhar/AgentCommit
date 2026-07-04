"use client";

import { signIn } from "next-auth/react";

type ProviderMap = Record<string, unknown>;

export async function signInWithGitHub() {
  const response = await fetch("/api/auth/providers");
  if (!response.ok) {
    throw new Error("Auth is not available. Check the frontend server logs.");
  }

  const providers = (await response.json()) as ProviderMap;
  if (!("github" in providers)) {
    window.alert(
      "GitHub OAuth is not configured yet. Add AUTH_GITHUB_ID, AUTH_GITHUB_SECRET, and AUTH_SECRET to frontend/.env.local, then restart npm run dev.",
    );
    return;
  }

  await signIn("github", { callbackUrl: "/dashboard" });
}

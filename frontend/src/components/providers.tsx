"use client";

import { SessionProvider } from "next-auth/react";
import type { ReactNode } from "react";

interface ProvidersProps {
  children: ReactNode;
}

/**
 * Client-side providers wrapper.
 * Wraps the app with NextAuth SessionProvider for auth state.
 */
export function Providers({ children }: ProvidersProps) {
  return <SessionProvider>{children}</SessionProvider>;
}

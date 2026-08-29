import type { NextConfig } from "next";

// Server-side origin for the FastAPI backend. Read here (not as NEXT_PUBLIC_*)
// because the rewrite runs in the Next.js server, never in the browser — the
// browser only ever calls the same-origin /api/proxy/* path below. Falls back to
// the local dev backend so `npm run dev` keeps working with no .env.local set.
const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/proxy/:path*",
        destination: `${BACKEND_API_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;

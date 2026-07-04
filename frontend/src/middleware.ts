/**
 * Middleware for protecting authenticated routes.
 *
 * Redirects unauthenticated users to the landing page
 * when they try to access /dashboard or /issue/* routes.
 */

export { auth as middleware } from "@/lib/auth";

export const config = {
  matcher: ["/dashboard/:path*", "/issue/:path*"],
};

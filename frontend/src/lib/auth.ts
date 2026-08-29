/**
 * NextAuth.js v5 configuration with GitHub OAuth provider.
 *
 * This is the central auth config used by the route handler and middleware.
 */

import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    GitHub({
      clientId: process.env.AUTH_GITHUB_ID,
      clientSecret: process.env.AUTH_GITHUB_SECRET,
      authorization: {
        params: {
          scope: "read:user repo read:org",
        },
      },
    }),
  ],
  callbacks: {
    /** Forward the GitHub access token and login into the JWT. */
    async jwt({ token, account, profile }) {
      if (account) {
        token.accessToken = account.access_token;
      }
      if (profile) {
        token.username = (profile as Record<string, unknown>).login as string;
      }
      return token;
    },
    /** Expose the access token and GitHub username in the client-side session. */
    async session({ session, token }) {
      session.accessToken = token.accessToken as string;
      session.username = (token.username as string) ?? "";
      return session;
    },
    /**
     * Gate protected routes. Without this callback next-auth v5's default is to
     * allow every request through, so `middleware.ts`'s matcher on /dashboard and
     * /issue/* would do nothing — protection would be client-side only, and every
     * protected page's shell would render (and flash) before its own redirect fires.
     */
    authorized({ auth: session }) {
      return Boolean(session?.user);
    },
  },
  pages: {
    signIn: "/",
  },
});

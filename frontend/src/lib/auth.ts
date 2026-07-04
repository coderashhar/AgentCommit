import NextAuth, { type NextAuthConfig } from "next-auth";
import GitHub from "next-auth/providers/github";

const githubClientId = process.env.AUTH_GITHUB_ID ?? process.env.GITHUB_CLIENT_ID;
const githubClientSecret =
  process.env.AUTH_GITHUB_SECRET ?? process.env.GITHUB_CLIENT_SECRET;
const isProduction = process.env.NODE_ENV === "production";
const authSecret =
  process.env.AUTH_SECRET ??
  process.env.NEXTAUTH_SECRET ??
  (isProduction ? undefined : "agentcommit-local-development-auth-secret");
const providers =
  githubClientId && githubClientSecret
    ? [
        GitHub({
          clientId: githubClientId,
          clientSecret: githubClientSecret,
          authorization: {
            params: {
              scope: "read:user repo read:org",
            },
          },
        }),
      ]
    : [];

const config = {
  secret: authSecret,
  trustHost: true,
  providers,
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
      }

      if (
        profile &&
        typeof profile === "object" &&
        "login" in profile &&
        typeof profile.login === "string"
      ) {
        token.username = profile.login;
      }

      return token;
    },
    async session({ session, token }) {
      session.accessToken =
        typeof token.accessToken === "string" ? token.accessToken : "";
      session.username =
        typeof token.username === "string"
          ? token.username
          : session.user?.name ?? "";

      return session;
    },
  },
} satisfies NextAuthConfig;

export const { handlers, auth, signIn, signOut } = NextAuth(config);

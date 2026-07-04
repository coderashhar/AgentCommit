/**
 * Extend NextAuth types to include the GitHub access token in the session.
 */

import "next-auth";

declare module "next-auth" {
  interface Session {
    accessToken: string;
    username: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    username?: string;
  }
}

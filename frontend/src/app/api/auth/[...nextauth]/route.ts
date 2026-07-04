/**
 * NextAuth.js API route handler.
 * Handles /api/auth/* routes (signin, signout, callback, etc.)
 */

import { handlers } from "@/lib/auth";

const { GET, POST } = handlers;
export { GET, POST };

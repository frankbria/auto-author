"use client";

import { createAuthClient } from "better-auth/react";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_BETTER_AUTH_URL || "http://localhost:3000",
});

// Export hooks from authClient
export const { useSession } = authClient;

// Re-export auth methods for convenience
export const signIn = authClient.signIn;
export const signUp = authClient.signUp;
export const signOut = authClient.signOut;

// Note: better-auth doesn't require a SessionProvider wrapper like Clerk
// Sessions are managed via cookies and accessible through useSession hook

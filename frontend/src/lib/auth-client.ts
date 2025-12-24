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

// Password reset methods - use type assertion since they are available at runtime
// but may not be fully typed in the current better-auth version
export const forgetPassword = (authClient as any).forgetPassword;
export const resetPassword = (authClient as any).resetPassword;

// Note: better-auth doesn't require a SessionProvider wrapper like Clerk
// Sessions are managed via cookies and accessible through useSession hook

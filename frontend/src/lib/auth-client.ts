"use client";

import { createAuthClient } from "better-auth/react";

// Type definitions for password reset methods not fully typed in better-auth
interface PasswordResetMethods {
  forgetPassword: (options: {
    email: string;
    redirectTo?: string;
  }) => Promise<{ error?: { message: string } }>;
  resetPassword: (options: {
    newPassword: string;
    token?: string;
  }) => Promise<{ error?: { message: string } }>;
}

// Extend the auth client type to include password reset methods
type AuthClientWithPasswordReset = ReturnType<typeof createAuthClient> & PasswordResetMethods;

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_BETTER_AUTH_URL || "http://localhost:3000",
}) as AuthClientWithPasswordReset;

// Export hooks from authClient
export const { useSession } = authClient;

// Re-export auth methods for convenience
export const signIn = authClient.signIn;
export const signUp = authClient.signUp;
export const signOut = authClient.signOut;

// Password reset methods - properly typed via AuthClientWithPasswordReset
export const forgetPassword = authClient.forgetPassword;
export const resetPassword = authClient.resetPassword;

// Note: better-auth doesn't require a SessionProvider wrapper like Clerk
// Sessions are managed via cookies and accessible through useSession hook

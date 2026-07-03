"use client";

import { createAuthClient } from "better-auth/react";
import { twoFactorClient } from "better-auth/client/plugins";

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

// Built without a cast first so the twoFactor plugin's client methods keep
// their inferred types; password reset methods are layered on afterwards.
const baseAuthClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_BETTER_AUTH_URL || "http://localhost:3000",
  plugins: [
    twoFactorClient({
      // Sign-in responses flagged with twoFactorRedirect land on the TOTP page.
      onTwoFactorRedirect() {
        window.location.href = "/auth/verify-2fa";
      },
    }),
  ],
});

// Extend the auth client type to include password reset methods
type AuthClientWithPasswordReset = typeof baseAuthClient & PasswordResetMethods;

export const authClient = baseAuthClient as AuthClientWithPasswordReset;

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

"use client";

import { createAuthClient } from "better-auth/react";
import { twoFactorClient } from "better-auth/client/plugins";

// better-auth types the password-reset methods itself, so nothing is layered on
// top. A hand-rolled `PasswordResetMethods` interface used to declare
// `forgetPassword` here and the client was cast to it — which is exactly why
// better-auth 1.7 renaming that method to `requestPasswordReset` (the route moved
// from /forget-password to /request-password-reset) passed typecheck and shipped
// a 404 on the forgot-password page (#556). Declaring a library's surface by hand
// removes the compiler's ability to notice it changed; let inference do it.
export const authClient = createAuthClient({
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

// Export hooks from authClient
export const { useSession } = authClient;

// Re-export auth methods for convenience
export const signIn = authClient.signIn;
export const signUp = authClient.signUp;
export const signOut = authClient.signOut;

// Password reset methods, typed by better-auth itself
export const requestPasswordReset = authClient.requestPasswordReset;
export const resetPassword = authClient.resetPassword;

// Note: better-auth doesn't require a SessionProvider wrapper like Clerk
// Sessions are managed via cookies and accessible through useSession hook

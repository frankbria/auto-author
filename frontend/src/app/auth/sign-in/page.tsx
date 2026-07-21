"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authClient } from "@/lib/auth-client";
import { sanitizeRedirectPath } from "@/lib/security";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { HugeiconsIcon } from "@hugeicons/react";
import { ViewIcon, ViewOffIcon, Alert02Icon } from "@hugeicons/core-free-icons";
import Link from "next/link";

/**
 * Maps error messages to user-friendly text
 */
function getErrorMessage(error: { message?: string; code?: string } | null): string {
  if (!error) return "";

  const message = error.message?.toLowerCase() || "";
  const code = error.code?.toLowerCase() || "";

  // Check for specific error patterns
  if (
    message.includes("invalid") ||
    message.includes("incorrect") ||
    message.includes("wrong") ||
    code.includes("invalid_credentials")
  ) {
    return "Email or password is incorrect";
  }

  if (
    message.includes("not found") ||
    message.includes("no user") ||
    message.includes("no account") ||
    code.includes("user_not_found")
  ) {
    return "No account found with this email";
  }

  if (
    message.includes("locked") ||
    message.includes("blocked") ||
    message.includes("suspended") ||
    code.includes("account_locked")
  ) {
    return "Account temporarily locked. Try again later";
  }

  if (
    message.includes("rate") ||
    message.includes("limit") ||
    message.includes("too many") ||
    code.includes("rate_limit")
  ) {
    return "Too many attempts. Please try again later";
  }

  if (
    message.includes("network") ||
    message.includes("fetch") ||
    message.includes("connection")
  ) {
    return "Connection error. Please check your internet";
  }

  // Unmatched: show a safe generic message, never the raw backend text (#215).
  return "Failed to sign in. Please try again";
}

function SignInForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Only same-origin relative paths are honored; anything else falls back to
  // /dashboard (open-redirect hardening, issue #184).
  const redirect = sanitizeRedirectPath(searchParams.get("redirect"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const { data, error: signInError } = await authClient.signIn.email({
        email,
        password,
      });

      if (signInError) {
        setError(getErrorMessage(signInError));
        return;
      }

      // A 2FA-enabled account returns a twoFactorRedirect flag instead of a
      // session; the twoFactorClient handler navigates to /auth/verify-2fa.
      // That navigation drops the ?redirect deep-link (#237), so stash the
      // already-sanitized target for the verify page to pick up. Skip the
      // default /dashboard so an unstashed value there means "no deep-link".
      if (data && 'twoFactorRedirect' in data && (data as { twoFactorRedirect?: boolean }).twoFactorRedirect) {
        if (redirect !== '/dashboard') {
          sessionStorage.setItem('auth:postVerifyRedirect', redirect);
        }
        return;
      }

      // Success - redirect to dashboard or original destination
      router.push(redirect);
    } catch (err) {
      if (err instanceof Error) {
        if (err.message.includes("network") || err.message.includes("fetch")) {
          setError("Connection error. Please check your internet");
        } else {
          setError("Failed to sign in. Please try again");
        }
      } else {
        setError("An unexpected error occurred");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">Sign In</CardTitle>
          <CardDescription>
            Enter your email and password to access your account
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <HugeiconsIcon icon={Alert02Icon} size={16} />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link
                  href="/auth/forgot-password"
                  className="text-sm text-blue-600 hover:underline dark:text-blue-400"
                  tabIndex={-1}
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                  className="pr-10 max-md:pr-14"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center justify-center text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 max-md:min-h-11 max-md:min-w-11"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <HugeiconsIcon icon={ViewOffIcon} size={16} />
                  ) : (
                    <HugeiconsIcon icon={ViewIcon} size={16} />
                  )}
                </button>
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Signing in..." : "Sign In"}
            </Button>
            <p className="text-sm text-center text-gray-600 dark:text-gray-400">
              Don't have an account?{" "}
              <Link
                href="/auth/sign-up"
                className="text-blue-600 hover:underline dark:text-blue-400"
              >
                Sign up
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}

export default function SignInPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl">Sign In</CardTitle>
            <CardDescription>Loading...</CardDescription>
          </CardHeader>
        </Card>
      </div>
    }>
      <SignInForm />
    </Suspense>
  );
}

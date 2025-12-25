"use client";

import { useState, Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authClient } from "@/lib/auth-client";
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
import {
  PasswordRequirements,
  isPasswordValid,
} from "@/components/auth/PasswordRequirements";
import { CheckCircle, Eye, EyeOff, ArrowLeft, AlertCircle } from "lucide-react";
import Link from "next/link";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const urlError = searchParams.get("error");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  // Handle URL error parameter (invalid/expired token)
  useEffect(() => {
    if (urlError) {
      if (urlError === "INVALID_TOKEN" || urlError === "invalid_token") {
        setError("This reset link is invalid. Please request a new one");
      } else if (urlError === "EXPIRED_TOKEN" || urlError === "expired_token") {
        setError("This reset link has expired. Please request a new one");
      } else {
        setError("Invalid reset link. Please request a new one");
      }
    }
  }, [urlError]);

  // Check for missing token
  const hasValidToken = token && !urlError;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    // Validate passwords match
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    // Validate password requirements
    if (!isPasswordValid(password)) {
      setError("Password does not meet all requirements");
      return;
    }

    if (!token) {
      setError("Invalid reset link. Please request a new password reset");
      return;
    }

    setLoading(true);

    try {
      const { error: resetError } = await (authClient as any).resetPassword({
        newPassword: password,
        token,
      });

      if (resetError) {
        // Map specific errors to user-friendly messages
        const errorMessage = resetError.message?.toLowerCase() || "";
        if (errorMessage.includes("expired")) {
          setError("This reset link has expired. Please request a new one");
        } else if (errorMessage.includes("invalid") || errorMessage.includes("token")) {
          setError("Invalid reset link. Please request a new one");
        } else if (errorMessage.includes("same")) {
          setError("New password cannot be the same as your old password");
        } else {
          setError(resetError.message || "Failed to reset password");
        }
        return;
      }

      setSuccess(true);
      // Redirect to sign-in after 3 seconds
      setTimeout(() => {
        router.push("/auth/sign-in");
      }, 3000);
    } catch (err) {
      if (err instanceof Error) {
        if (err.message.includes("network") || err.message.includes("fetch")) {
          setError("Connection error. Please check your internet");
        } else {
          setError(err.message);
        }
      } else {
        setError("An unexpected error occurred. Please try again");
      }
    } finally {
      setLoading(false);
    }
  }

  // Success state
  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
              <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <CardTitle className="text-2xl">Password Reset</CardTitle>
            <CardDescription className="mt-2">
              Your password has been successfully reset
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Alert>
              <AlertDescription>
                Redirecting you to sign in...
              </AlertDescription>
            </Alert>
          </CardContent>
          <CardFooter>
            <Link href="/auth/sign-in" className="w-full">
              <Button className="w-full">Sign In Now</Button>
            </Link>
          </CardFooter>
        </Card>
      </div>
    );
  }

  // Invalid/missing token state
  if (!hasValidToken) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-900">
              <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
            <CardTitle className="text-2xl">Invalid Reset Link</CardTitle>
            <CardDescription className="mt-2">
              {error || "This password reset link is invalid or has expired"}
            </CardDescription>
          </CardHeader>
          <CardFooter className="flex flex-col space-y-4">
            <Link href="/auth/forgot-password" className="w-full">
              <Button className="w-full">Request New Link</Button>
            </Link>
            <Link
              href="/auth/sign-in"
              className="flex items-center justify-center gap-2 text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to sign in
            </Link>
          </CardFooter>
        </Card>
      </div>
    );
  }

  // Password match validation
  const passwordsMatch = password === confirmPassword || confirmPassword === "";

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">Reset Password</CardTitle>
          <CardDescription>Enter your new password below</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <div className="space-y-2">
              <Label htmlFor="password">New Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              <PasswordRequirements password={password} showStrength />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm New Password</Label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  disabled={loading}
                  className={`pr-10 ${
                    !passwordsMatch
                      ? "border-red-500 focus-visible:ring-red-500"
                      : ""
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  aria-label={
                    showConfirmPassword ? "Hide password" : "Show password"
                  }
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {!passwordsMatch && (
                <p className="text-sm text-red-500">Passwords do not match</p>
              )}
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button
              type="submit"
              className="w-full"
              disabled={loading || !isPasswordValid(password) || !passwordsMatch}
            >
              {loading ? "Resetting..." : "Reset Password"}
            </Button>
            <Link
              href="/auth/sign-in"
              className="flex items-center justify-center gap-2 text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to sign in
            </Link>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle className="text-2xl">Reset Password</CardTitle>
              <CardDescription>Loading...</CardDescription>
            </CardHeader>
          </Card>
        </div>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}

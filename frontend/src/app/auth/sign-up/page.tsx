"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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
import { Eye, EyeOff, AlertCircle } from "lucide-react";
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
    message.includes("exists") ||
    message.includes("already") ||
    message.includes("duplicate") ||
    code.includes("user_exists") ||
    code.includes("email_exists")
  ) {
    return "An account with this email already exists";
  }

  if (
    message.includes("invalid email") ||
    message.includes("email format") ||
    code.includes("invalid_email")
  ) {
    return "Please enter a valid email address";
  }

  if (
    message.includes("password") &&
    (message.includes("weak") || message.includes("requirements"))
  ) {
    return "Password does not meet security requirements";
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

  // Return original message if no pattern matched
  return error.message || "Unable to create account. Please try again later";
}

export default function SignUpPage() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Email validation
  const isEmailValid = email === "" || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  const emailTouched = email.length > 0;

  // Password match validation
  const passwordsMatch = password === confirmPassword || confirmPassword === "";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    // Validate email format
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Please enter a valid email address");
      return;
    }

    // Validate passwords match
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    // Validate password requirements using the component's validation
    if (!isPasswordValid(password)) {
      setError("Password does not meet all requirements");
      return;
    }

    setLoading(true);

    try {
      const { data, error: signUpError } = await authClient.signUp.email({
        email,
        password,
        name,
      });

      if (signUpError) {
        setError(getErrorMessage(signUpError));
        return;
      }

      // Success - redirect to dashboard
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof Error) {
        if (err.message.includes("network") || err.message.includes("fetch")) {
          setError("Connection error. Please check your internet");
        } else {
          setError(err.message);
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
          <CardTitle className="text-2xl">Create Account</CardTitle>
          <CardDescription>
            Sign up to start creating your books
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                type="text"
                placeholder="John Doe"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                disabled={loading}
              />
            </div>
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
                className={
                  emailTouched && !isEmailValid
                    ? "border-red-500 focus-visible:ring-red-500"
                    : ""
                }
              />
              {emailTouched && !isEmailValid && (
                <p className="text-sm text-red-500">
                  Please enter a valid email address
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
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
                  tabIndex={-1}
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
              <Label htmlFor="confirmPassword">Confirm Password</Label>
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
                  tabIndex={-1}
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
              {loading ? "Creating account..." : "Sign Up"}
            </Button>
            <p className="text-sm text-center text-gray-600 dark:text-gray-400">
              Already have an account?{" "}
              <Link
                href="/auth/sign-in"
                className="text-blue-600 hover:underline dark:text-blue-400"
              >
                Sign in
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}

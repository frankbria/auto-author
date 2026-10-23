import Link from "next/link";
import { redirect } from "next/navigation";
import { sanitizeRedirectPath } from "@/lib/security";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type SearchParams = Record<string, string | string[] | undefined>;

/**
 * Where an emailed verification link lands (#969). better-auth's /verify-email
 * redirects here, appending `?error=TOKEN_EXPIRED` (or INVALID_TOKEN,
 * USER_NOT_FOUND) when the link fails. The page is public so a signed-out
 * visitor keeps that query; without an error it forwards to `next`.
 */
export default async function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const { error, next } = await searchParams;
  const destination = sanitizeRedirectPath(typeof next === "string" ? next : null);

  if (!error) redirect(destination);

  const expired = error === "TOKEN_EXPIRED";

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">
            <h1>
              {expired
                ? "This verification link has expired"
                : "This verification link is not valid"}
            </h1>
          </CardTitle>
          <CardDescription>
            {expired
              ? "Links work for one hour after they are sent."
              : "Part of it may be missing, or the account it was sent for no longer exists."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            To get a new link,{" "}
            <Link
              href={`/auth/sign-in?redirect=${encodeURIComponent(destination)}`}
              className="text-primary hover:underline"
            >
              sign in
            </Link>{" "}
            with your email and password and we will email you a fresh one.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

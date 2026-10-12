import { NextResponse } from "next/server";
import { emailProvider } from "@/lib/email";

// Read the environment on every request: a prerendered answer would report the
// build machine's settings, not the running container's.
export const dynamic = "force-dynamic";

/**
 * Public, unauthenticated health signal for what only the frontend knows (#968).
 * Since #792 nobody can finish signing up without the verification email, and a
 * missing provider is invisible to the user. Reports the provider's name, never
 * the key or the from-address.
 */
export function GET() {
  const provider = emailProvider();
  return NextResponse.json(
    { status: "ok", email: { configured: provider !== null, provider } },
    { headers: { "Cache-Control": "no-store" } }
  );
}

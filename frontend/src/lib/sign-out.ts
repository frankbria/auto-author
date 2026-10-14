import { authClient } from "@/lib/auth-client";
import { toast } from "@/lib/toast";

// Until when a sign-out the user asked for owns the navigation: open-ended
// while the request runs, then long enough for the caller's router.push.
const CALLER_NAVIGATES_WITHIN_MS = 5000;
let underwayUntil = 0;

/**
 * True while a sign-out the user asked for is running and for a few seconds
 * after it succeeds. ProtectedRoute and the 401 handler leave the navigation
 * to the caller meanwhile, or their own redirect would win the race and send
 * the user to sign-in with a way back to the page they just left (#886).
 * Bounded, so a protected page reached later redirects as usual.
 */
export const signOutUnderway = () => Date.now() < underwayUntil;
export const endSignOut = () => {
  underwayUntil = 0;
};

/**
 * Signs the user out and says so when it fails (#796). The client resolves
 * with `{ error }` when refused and throws when the request never arrives;
 * either way the session is still alive, so the caller must not carry on as
 * if it had worked. Returns whether the sign-out happened.
 */
export async function signOutOrNotify({ quiet = false } = {}): Promise<boolean> {
  underwayUntil = Infinity;
  const failed = await authClient.signOut().then(
    ({ error }) => Boolean(error),
    () => true
  );
  underwayUntil = failed ? 0 : Date.now() + CALLER_NAVIGATES_WITHIN_MS;
  if (failed && !quiet) {
    toast({
      title: "Could not sign out",
      description: "You are still signed in. Check your connection and try again.",
      variant: "destructive",
    });
  }
  return !failed;
}

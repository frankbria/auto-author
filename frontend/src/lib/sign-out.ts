import { authClient } from "@/lib/auth-client";
import { toast } from "@/lib/toast";

let underway = false;

/**
 * True from the moment a sign-out the user asked for starts until a session is
 * seen again. ProtectedRoute leaves the navigation to the caller meanwhile, or
 * its own redirect would win the race and send the user to sign-in with a way
 * back to the page they just left (#886).
 */
export const signOutUnderway = () => underway;
export const endSignOut = () => {
  underway = false;
};

/**
 * Signs the user out and says so when it fails (#796). The client resolves
 * with `{ error }` when refused and throws when the request never arrives;
 * either way the session is still alive, so the caller must not carry on as
 * if it had worked. Returns whether the sign-out happened.
 */
export async function signOutOrNotify({ quiet = false } = {}): Promise<boolean> {
  underway = true;
  const failed = await authClient.signOut().then(
    ({ error }) => Boolean(error),
    () => true
  );
  if (failed) underway = false;
  if (failed && !quiet) {
    toast({
      title: "Could not sign out",
      description: "You are still signed in. Check your connection and try again.",
      variant: "destructive",
    });
  }
  return !failed;
}

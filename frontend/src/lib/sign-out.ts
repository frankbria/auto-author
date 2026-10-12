import { authClient } from "@/lib/auth-client";
import { toast } from "@/lib/toast";

/**
 * Signs the user out and says so when it fails (#796). The client resolves
 * with `{ error }` when refused and throws when the request never arrives;
 * either way the session is still alive, so the caller must not carry on as
 * if it had worked. Returns whether the sign-out happened.
 */
export async function signOutOrNotify(): Promise<boolean> {
  const failed = await authClient.signOut().then(
    ({ error }) => Boolean(error),
    () => true
  );
  if (failed) {
    toast({
      title: "Could not sign out",
      description: "You are still signed in. Check your connection and try again.",
      variant: "destructive",
    });
  }
  return !failed;
}

import { authClient } from "@/lib/auth-client";
import { toast } from "@/lib/toast";
import { closeTermsExits } from "@/lib/terms-exits";
import { clearLocalWriting, hasUnsavedLocalWriting } from "@/lib/storage/localWriting";

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

let signOuts = 0;
/**
 * How many sign-outs the user asked for have succeeded in this tab (#1091).
 * Writing code records it when it starts (a save, an editor); if it has moved
 * by the time a save fails, the user has signed out since, and the text is
 * not written back to the browser they just cleared. Unlike signOutUnderway(),
 * this does not expire, however slowly a request fails.
 */
export const signOutCount = () => signOuts;

/** Resolves true when it leaves text that never reached the server. */
type BeforeSignOut = () => Promise<boolean | void>;
const beforeSignOutHandlers = new Set<BeforeSignOut>();

/**
 * Work an explicit sign-out waits for, while the session can still save (#1091):
 * an open editor's edit still inside its autosave delay. A handler resolves
 * true when text is still unsaved afterwards, which the user is then asked
 * about even if the browser could not store a copy of it (a full or blocked
 * localStorage). Returns the unregister function, so it can be a React
 * effect's cleanup.
 */
export function beforeSignOut(handler: BeforeSignOut): () => void {
  beforeSignOutHandlers.add(handler);
  return () => {
    beforeSignOutHandlers.delete(handler);
  };
}

const pendingSaves = new Set<Promise<unknown>>();
// What a failed leaving save left unsaved, by key: kept here as well as in the
// browser's backup, since storing that backup can itself fail (full storage).
const leftUnsavedOnLeaving = new Set<string>();

/**
 * A save from a page or editor that is already gone (its leaving flush, #1091),
 * resolving whether its text reached the server. No beforeSignOut handler
 * covers it any more, so a sign-out waits for it before deciding, and asks if
 * it failed, even when no backup could be stored. `key` names the text (one
 * chapter, one summary), so a later save of it clears the mark (savedNow).
 * `startedIn`: the signOutCount() its editor opened in; a save from an editor
 * that outlived a sign-out marks nothing.
 */
export function trackSave(key: string, save: Promise<boolean>, startedIn = signOutCount()): Promise<boolean> {
  pendingSaves.add(save);
  const settled = (saved: boolean) => {
    pendingSaves.delete(save);
    if (signOuts !== startedIn) return;
    if (saved) leftUnsavedOnLeaving.delete(key);
    else leftUnsavedOnLeaving.add(key);
  };
  save.then(settled, () => settled(false));
  return save;
}

/** Tests only: forget failed leaving saves from an earlier test. */
export function resetLeavingSavesForTests() {
  leftUnsavedOnLeaving.clear();
}

/** The text under `key` has reached the server since a leaving save failed. */
export function savedNow(key: string) {
  leftUnsavedOnLeaving.delete(key);
}

/** Waits until no tracked save is running, including ones started meanwhile. */
async function settleTrackedSaves() {
  while (pendingSaves.size > 0) {
    await Promise.all([...pendingSaves].map((save) => save.catch(() => {})));
  }
}

export const UNSAVED_WRITING_WARNING =
  "Some of your writing could not be saved to your account and is only in this browser. " +
  "Signing out removes it from this browser. Sign out anyway?";

/**
 * Signs the user out and says so when it fails (#796). The client resolves
 * with `{ error }` when refused and throws when the request never arrives;
 * either way the session is still alive, so the caller must not carry on as
 * if it had worked. Returns whether the sign-out happened.
 *
 * A sign-out removes the user's writing from this browser (#1091), so the next
 * person at a shared device cannot read it. Edits still waiting to save are
 * saved first; if any text still never reached the server, the user is asked
 * before it is discarded, and a "no" leaves them signed in with it kept. The
 * 401 path (`lib/api/unauthorized.ts`) never comes here: a session that
 * expired mid-edit keeps its backups, since they may be the only copy.
 *
 * `leavePage`: hold the redirect guards until the page is replaced, for a
 * caller that follows a success with a full-page load rather than router.push.
 */
export async function signOutOrNotify({
  quiet = false,
  leavePage = false,
} = {}): Promise<boolean> {
  await settleTrackedSaves();
  const leftUnsaved = await Promise.all(
    [...beforeSignOutHandlers].map((handler) => handler().then((unsaved) => unsaved === true, () => true))
  );
  // An editor closed while the handlers ran hands its edit to a leaving save.
  await settleTrackedSaves();
  const unsaved = leftUnsaved.includes(true) || leftUnsavedOnLeaving.size > 0 || hasUnsavedLocalWriting();
  if (unsaved && !window.confirm(UNSAVED_WRITING_WARNING)) return false;
  underwayUntil = Infinity;
  const failed = await authClient.signOut().then(
    ({ error }) => Boolean(error),
    () => true
  );
  // leavePage: the caller replaces the document, which resets this module, so
  // no timer can expire before a slow navigation lands (#1177).
  underwayUntil = failed ? 0 : leavePage ? Infinity : Date.now() + CALLER_NAVIGATES_WITHIN_MS;
  // The next sign-in in this tab is asked about the Terms again (#961).
  if (!failed) {
    signOuts += 1;
    closeTermsExits();
    clearLocalWriting();
    leftUnsavedOnLeaving.clear();
  }
  if (failed && !quiet) {
    toast({
      title: "Could not sign out",
      description: "You are still signed in. Check your connection and try again.",
      variant: "destructive",
    });
  }
  return !failed;
}

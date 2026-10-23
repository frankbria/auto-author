import type { Db } from "mongodb";
import { isAPIError } from "better-auth/api";

// The better-auth endpoints through which a signed-in user changes their second factor.
const SECOND_FACTOR_CHANGES = new Set([
  "/two-factor/verify-totp",
  "/two-factor/disable",
  "/two-factor/generate-backup-codes",
]);

type SessionRef = { session: { token: string }; user: { id: string } };

interface AfterHookContext {
  path?: string;
  context: {
    returned?: unknown;
    session: SessionRef | null;
    newSession: SessionRef | null;
    internalAdapter: {
      listSessions(userId: string): Promise<{ token: string }[]>;
      deleteSessions(tokens: string[]): Promise<void>;
    };
  };
}

/**
 * better-auth after-hook (#972). A second-factor change ends every other
 * session of the account in the same request, so one an attacker already
 * holds cannot outlive the change meant to lock them out. better-auth itself
 * rotates only the session that made the change.
 */
export async function endOtherSessionsOnSecondFactorChange(ctx: AfterHookContext) {
  if (!SECOND_FACTOR_CHANGES.has(ctx.path ?? "") || isAPIError(ctx.context.returned)) return;
  // The session the request came in with. verify-totp finishing a sign-in has none.
  const caller = ctx.context.session;
  if (!caller) return;
  // verify-totp rotates the session only when it turns 2FA on; a signed-in
  // user merely re-checking a code changes nothing.
  if (ctx.path === "/two-factor/verify-totp" && !ctx.context.newSession) return;
  // enable and disable replaced the caller's session with this new one.
  const keep = (ctx.context.newSession ?? caller).session.token;
  const sessions = await ctx.context.internalAdapter.listSessions(caller.user.id);
  await ctx.context.internalAdapter.deleteSessions(
    sessions.map((s) => s.token).filter((token) => token !== keep)
  );
}

/**
 * A password reset forgets every device the account trusted to skip the
 * second factor (#972). The two-factor plugin keeps each as a `trust-device-*`
 * verification row whose value is the user id, and clears them only on disable.
 */
export async function forgetTrustedDevices(database: Db, userId: string) {
  await database
    .collection("verification")
    .deleteMany({ value: userId, identifier: /^trust-device-/ });
}

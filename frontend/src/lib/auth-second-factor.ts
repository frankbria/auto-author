import type { Db } from "mongodb";
import * as Sentry from "@sentry/nextjs";
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
  json(body: Record<string, unknown>): unknown;
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

function reportFailure(operation: string, error: unknown) {
  // Reporting must not throw either: the callers promise never to.
  try {
    console.error(`Auth ${operation} failed:`, error);
    Sentry.captureException(error, { tags: { feature: "auth", operation } });
  } catch {
    // Nothing left to report to.
  }
}

/** Runs `step`, once more if it throws; true when either attempt succeeded. */
async function withOneRetry(operation: string, step: () => Promise<unknown>) {
  for (let attempt = 1; attempt <= 2; attempt++) {
    try {
      await step();
      return true;
    } catch (error) {
      if (attempt === 2) reportFailure(operation, error);
    }
  }
  return false;
}

/**
 * better-auth after-hook (#972). A second-factor change ends every other
 * session of the account in the same request, so one an attacker already
 * holds cannot outlive the change meant to lock them out. better-auth itself
 * rotates only the session that made the change. Disabling 2FA also forgets
 * every trusted device, where better-auth forgets only the caller's.
 *
 * If a step fails, the change's own answer is kept and flagged rather than
 * replaced by an error: the change has already happened, and for regenerated
 * backup codes an error would lose the only copy of the new codes. The flags
 * are `otherSessionsEnded: false` and, on disable, `trustedDevicesForgotten: false`.
 */
export async function endOtherSessionsOnSecondFactorChange(ctx: AfterHookContext, database: Db) {
  if (!SECOND_FACTOR_CHANGES.has(ctx.path ?? "") || isAPIError(ctx.context.returned)) return;
  // The session the request came in with. verify-totp finishing a sign-in has none.
  const caller = ctx.context.session;
  if (!caller) return;
  // verify-totp rotates the session only when it turns 2FA on; a signed-in
  // user merely re-checking a code changes nothing.
  if (ctx.path === "/two-factor/verify-totp" && !ctx.context.newSession) return;

  const flags: Record<string, false> = {};
  if (ctx.path === "/two-factor/disable" && !(await forgetTrustedDevices(database, caller.user.id))) {
    flags.trustedDevicesForgotten = false;
  }

  // enable and disable replaced the caller's session with this new one.
  const keep = (ctx.context.newSession ?? caller).session.token;
  const { internalAdapter } = ctx.context;
  const ended = await withOneRetry("end-other-sessions", async () => {
    const sessions = await internalAdapter.listSessions(caller.user.id);
    await internalAdapter.deleteSessions(
      sessions.map((s) => s.token).filter((token) => token !== keep)
    );
  });
  if (!ended) flags.otherSessionsEnded = false;
  if (Object.keys(flags).length) return ctx.json({ ...(ctx.context.returned as object), ...flags });
}

/**
 * Forgets every device the account trusted to skip the second factor (#972),
 * on a password reset and on disabling 2FA. The two-factor plugin keeps each
 * as a `trust-device-*` verification row whose value is the user id.
 *
 * Never throws, and resolves false when the rows could not be deleted: on a
 * reset, better-auth ends the account's sessions only after this returns, and
 * that must happen even when this cleanup fails.
 */
export async function forgetTrustedDevices(database: Db, userId: string) {
  return withOneRetry("forget-trusted-devices", () =>
    database.collection("verification").deleteMany({ value: userId, identifier: /^trust-device-/ })
  );
}

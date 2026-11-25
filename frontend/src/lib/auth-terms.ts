import { createAuthEndpoint, sessionMiddleware } from "better-auth/api";
import { TERMS_VERSION } from "./constants/legal";

/**
 * Where better-auth keeps the Terms acceptance on its user row (#789).
 * `input: false` makes better-auth refuse either field in a sign-up body, so
 * the browser cannot choose what was accepted or when.
 */
export const termsAcceptanceFields = {
  termsVersion: { type: "string", required: false, input: false },
  termsAcceptedAt: { type: "date", required: false, input: false },
} as const;

/** What the server records as accepted: the current version, now. */
const acceptedNow = () => ({ termsVersion: TERMS_VERSION, termsAcceptedAt: new Date() });

/**
 * better-auth `user.create.before` hook. The sign-up form is the only thing
 * that creates a user and it states the agreement above its button; a second
 * way to create one (a social provider) must show the same notice.
 */
export async function stampTermsAcceptance<T extends object>(user: T) {
  return { data: { ...user, ...acceptedNow() } };
}

interface AcceptTermsContext {
  json(body: { termsVersion: string }): unknown;
  context: {
    session: { user: { id: string } };
    internalAdapter: { updateUser(userId: string, data: Record<string, unknown>): Promise<unknown> };
  };
}

/**
 * An existing account accepts the current Terms (#961). The body is never
 * read: the server chooses the version and the time, as at sign-up. Since
 * #1263 this is the one users document the backend reads too, so its user and
 * the record kept at deletion carry the new acceptance with no copy to update.
 */
export async function acceptCurrentTerms(ctx: AcceptTermsContext) {
  await ctx.context.internalAdapter.updateUser(ctx.context.session.user.id, acceptedNow());
  return ctx.json({ termsVersion: TERMS_VERSION });
}

/**
 * `POST /api/auth/terms/accept`, for the signed-in user. better-auth's router
 * runs its origin check on every POST, so another site cannot submit it.
 */
export const termsAcceptance = () => ({
  id: "terms-acceptance" as const,
  endpoints: {
    acceptTerms: createAuthEndpoint(
      "/terms/accept",
      { method: "POST", use: [sessionMiddleware] },
      (ctx) => acceptCurrentTerms(ctx)
    ),
  },
});

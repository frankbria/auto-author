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

/**
 * better-auth `user.create.before` hook. The sign-up form is the only thing
 * that creates a user and it states the agreement above its button; a second
 * way to create one (a social provider) must show the same notice.
 */
export async function stampTermsAcceptance<T extends object>(user: T) {
  return {
    data: { ...user, termsVersion: TERMS_VERSION, termsAcceptedAt: new Date() },
  };
}

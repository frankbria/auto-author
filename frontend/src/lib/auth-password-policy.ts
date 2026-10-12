import { APIError } from "better-auth/api";
import { isPasswordValid } from "./password-policy";

// The request field that carries a NEW password, by better-auth endpoint.
// Sign-in is absent on purpose: an existing account's password is not judged.
const NEW_PASSWORD_FIELD = new Map([
  ["/sign-up/email", "password"],
  ["/reset-password", "newPassword"],
  ["/change-password", "newPassword"],
]);

/**
 * Refuses a new password the sign-up page's checklist would refuse (#794). The
 * checklist runs in the browser, so without this a direct request could set
 * any eight characters. Runs before every better-auth request.
 */
export async function rejectWeakPassword(ctx: { path?: string; body?: unknown }) {
  const field = NEW_PASSWORD_FIELD.get(ctx.path ?? "");
  if (!field) return;
  const password = (ctx.body as Record<string, unknown> | undefined)?.[field];
  if (typeof password !== "string" || !isPasswordValid(password)) {
    throw new APIError("BAD_REQUEST", {
      message:
        "Password must be at least 8 characters and include an uppercase letter, a lowercase letter and a number.",
    });
  }
}

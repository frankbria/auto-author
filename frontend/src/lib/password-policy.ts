/**
 * The password rule, in one place for the browser's checklist
 * (`PasswordRequirements`) and the server's refusal (`auth-password-policy`).
 */

export interface PasswordValidation {
  minLength: boolean;
  hasUppercase: boolean;
  hasLowercase: boolean;
  hasNumber: boolean;
}

/**
 * Validates a password against all requirements. The letter classes are ASCII
 * on purpose: this is the rule the pages have always shown, unchanged.
 */
export function validatePassword(password: string): PasswordValidation {
  return {
    minLength: password.length >= 8,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumber: /[0-9]/.test(password),
  };
}

/**
 * Checks if all password requirements are met
 */
export function isPasswordValid(password: string): boolean {
  const validation = validatePassword(password);
  return (
    validation.minLength &&
    validation.hasUppercase &&
    validation.hasLowercase &&
    validation.hasNumber
  );
}

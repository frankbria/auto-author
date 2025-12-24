"use client";

import { Check, X } from "lucide-react";

export interface PasswordValidation {
  minLength: boolean;
  hasUppercase: boolean;
  hasLowercase: boolean;
  hasNumber: boolean;
}

export interface PasswordRequirementsProps {
  password: string;
  showStrength?: boolean;
  className?: string;
}

/**
 * Validates a password against all requirements
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

/**
 * Calculates password strength as a percentage
 */
export function getPasswordStrength(password: string): {
  percentage: number;
  label: "weak" | "medium" | "strong";
} {
  const validation = validatePassword(password);
  const metCount = [
    validation.minLength,
    validation.hasUppercase,
    validation.hasLowercase,
    validation.hasNumber,
  ].filter(Boolean).length;

  const percentage = (metCount / 4) * 100;

  if (percentage <= 50) {
    return { percentage, label: "weak" };
  } else if (percentage <= 75) {
    return { percentage, label: "medium" };
  }
  return { percentage, label: "strong" };
}

interface RequirementItemProps {
  met: boolean;
  text: string;
}

function RequirementItem({ met, text }: RequirementItemProps) {
  return (
    <li className={`flex items-center gap-2 text-sm ${met ? "text-green-600 dark:text-green-400" : "text-muted-foreground"}`}>
      {met ? (
        <Check className="h-4 w-4" aria-hidden="true" />
      ) : (
        <X className="h-4 w-4 text-red-500" aria-hidden="true" />
      )}
      <span>{text}</span>
    </li>
  );
}

/**
 * Password requirements display component with real-time validation feedback
 */
export function PasswordRequirements({
  password,
  showStrength = false,
  className = "",
}: PasswordRequirementsProps) {
  const validation = validatePassword(password);
  const strength = getPasswordStrength(password);

  const strengthColors = {
    weak: "bg-red-500",
    medium: "bg-yellow-500",
    strong: "bg-green-500",
  };

  return (
    <div className={`space-y-2 ${className}`}>
      {showStrength && password.length > 0 && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Password strength</span>
            <span
              className={
                strength.label === "weak"
                  ? "text-red-500"
                  : strength.label === "medium"
                  ? "text-yellow-600 dark:text-yellow-400"
                  : "text-green-600 dark:text-green-400"
              }
            >
              {strength.label.charAt(0).toUpperCase() + strength.label.slice(1)}
            </span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-gray-200 dark:bg-gray-700">
            <div
              className={`h-full rounded-full transition-all duration-300 ${strengthColors[strength.label]}`}
              style={{ width: `${strength.percentage}%` }}
              role="progressbar"
              aria-valuenow={strength.percentage}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Password strength: ${strength.label}`}
            />
          </div>
        </div>
      )}
      <ul className="space-y-1" aria-label="Password requirements">
        <RequirementItem
          met={validation.minLength}
          text="At least 8 characters"
        />
        <RequirementItem
          met={validation.hasUppercase}
          text="At least one uppercase letter"
        />
        <RequirementItem
          met={validation.hasLowercase}
          text="At least one lowercase letter"
        />
        <RequirementItem
          met={validation.hasNumber}
          text="At least one number"
        />
      </ul>
    </div>
  );
}

export default PasswordRequirements;

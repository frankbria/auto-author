import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * @deprecated This function is deprecated and should not be used.
 *
 * For client components: Use the useAuthFetch hook from '@/hooks/useAuthFetch'
 * For server components: Use proper better-auth server-side authentication
 *
 * This function has been disabled for security reasons.
 */
export async function authFetch(url: string, options: RequestInit = {}): Promise<never> {
  throw new Error(
    'authFetch is deprecated and disabled for security reasons. ' +
    'Use useAuthFetch hook in client components or proper server-side auth.'
  );
}

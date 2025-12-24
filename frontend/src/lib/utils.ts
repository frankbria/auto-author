import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Simple auth fetch utility for making authenticated API requests
 * Note: This is a basic implementation. For client components, use useAuthFetch hook instead.
 */
export async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  // This is a placeholder implementation
  // In practice, you should use the useAuthFetch hook for client components
  // or handle authentication server-side
  return fetch(url, options);
}

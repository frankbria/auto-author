"use client";

import { useSession } from "@/lib/auth-client";
import { useState, useCallback } from "react";

interface UseAuthFetchOptions {
  /** Base URL for API requests */
  baseUrl?: string;
}

interface FetchOptions extends RequestInit {
  /** If true, cookies won't be included in the request */
  skipAuth?: boolean;
}

/**
 * Hook to make authenticated API requests using cookie-based authentication.
 *
 * Authentication is handled automatically via httpOnly session cookies set by better-auth.
 * The browser will automatically include these cookies in requests when credentials: 'include'
 * is set.
 *
 * This hook should only be used in Client Components.
 */
export function useAuthFetch(options: UseAuthFetchOptions = {}) {
  const { data: session } = useSession();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const { baseUrl = "/api" } = options;

  /**
   * Make an authenticated fetch request.
   *
   * Authentication is handled automatically via session cookies.
   * The browser includes httpOnly cookies with the request when
   * credentials: 'include' is specified.
   */
  const authFetch = useCallback(
    async <T = unknown>(
      path: string,
      fetchOptions: FetchOptions = {}
    ): Promise<T> => {
      const { skipAuth = false, ...restOptions } = fetchOptions;

      setLoading(true);
      setError(null);

      try {
        // Construct the full URL
        const url = path.startsWith("http") ? path : `${baseUrl}${path}`;

        // Prepare headers
        const headersObj: Record<string, string> = {
          "Content-Type": "application/json",
          ...(restOptions.headers as Record<string, string>),
        };

        // Convert to HeadersInit
        const headers: HeadersInit = headersObj;

        // Make the request with credentials included for cookie-based auth
        // Browser automatically sends httpOnly cookies when credentials: 'include' is set
        const response = await fetch(url, {
          ...restOptions,
          headers,
          // Include credentials (cookies) for authenticated requests
          // This enables the browser to automatically send session cookies
          credentials: skipAuth ? "omit" : "include",
        });

        // Parse the response
        let data;
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          data = await response.json();
        } else {
          data = await response.text();
        }

        // Handle errors
        if (!response.ok) {
          throw new Error(
            typeof data === "object" && data.detail
              ? data.detail
              : `API request failed with status ${response.status}`
          );
        }

        return data as T;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [baseUrl]
  );

  /**
   * Check if user is authenticated based on session state.
   * Note: This is a convenience check - actual authentication is validated server-side.
   */
  const isAuthenticated = !!session?.user;

  return {
    authFetch,
    loading,
    error,
    isAuthenticated,
  };
}

export default useAuthFetch;

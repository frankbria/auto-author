"use client";

import { useAuth } from "@clerk/nextjs";
import { useState, useCallback } from "react";

interface UseAuthFetchOptions {
  /** Base URL for API requests */
  baseUrl?: string;
}

interface FetchOptions extends RequestInit {
  /** If true, the auth token won't be included in the request */
  skipAuth?: boolean;
}

/**
 * Hook to make authenticated API requests
 * This hook should only be used in Client Components
 */
export function useAuthFetch(options: UseAuthFetchOptions = {}) {
  const { getToken } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const { baseUrl = "/api" } = options;

  /**
   * Make an authenticated fetch request
   */
  const authFetch = useCallback(async <T = unknown>(
    path: string, 
    fetchOptions: FetchOptions = {}
  ): Promise<T> => {
    const { skipAuth = false, ...restOptions } = fetchOptions;
    
    setLoading(true);
    setError(null);
    
    try {
      // Construct the full URL
      const url = path.startsWith("http") ? path : `${baseUrl}${path}`;
        // Prepare headers - using let to allow reassignment
      let headersObj: Record<string, string> = {
        "Content-Type": "application/json",
        ...(restOptions.headers as Record<string, string>),
      };
        
      // Add auth token if authentication is not skipped
      if (!skipAuth) {
        const token = await getToken();
        if (token) {
          // Add authorization header
          headersObj = {
            ...headersObj,
            "Authorization": `Bearer ${token}`
          };
        }
      }
      
      // Convert to HeadersInit
      const headers: HeadersInit = headersObj;
      
      // Make the request
      const response = await fetch(url, {
        ...restOptions,
        headers,
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
      setError(err instanceof Error ? err : new Error(String(err)));
      throw err;
    } finally {
      setLoading(false);
    }
  }, [baseUrl, getToken]);

  return {
    authFetch,
    loading,
    error,
  };
}

export default useAuthFetch;

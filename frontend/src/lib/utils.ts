import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * IMPORTANT: This is a fallback implementation and not recommended.
 * 
 * For client components: Use the useAuthFetch hook from '@/hooks/useAuthFetch'
 * For server components: Use the getAuthToken function from '@/lib/clerk-helpers'
 * 
 * This function attempts to work in both client and server contexts but has limitations.
 * 
 * @param url - The URL to fetch
 * @param options - Fetch options
 * @returns The fetch response
 */
export async function authFetch(url: string, options: RequestInit = {}) {
  try {
    let token = null;
    
    // Check if we're in a browser environment
    if (typeof window !== 'undefined') {
      // Client-side: We should ideally use the useAuth() hook from Clerk,
      // but since hooks can only be used in components, we use this fallback
      
      // Try to get the token from document cookies
      const cookies = document.cookie.split(';');
      const clerkCookie = cookies.find(c => c.trim().startsWith('__session='));
      if (clerkCookie) {
        token = clerkCookie.split('=')[1].trim();
      }
    } else {
      // Server-side: We need to use Clerk's server API
      // This won't work here, but it's a reminder to use the proper server-side approach
      // const { getToken } = auth();
      // token = await getToken();
      console.warn('authFetch was called in a server context. Use getAuthToken from clerk-helpers.ts instead.');
    }

    // If token is still null, we'll proceed without authentication
    // Add headers, including Authorization if we have a token
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
      ...(token && { Authorization: `Bearer ${token}` })
    };

    // Make the fetch request
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Check if the response is JSON
    const contentType = response.headers.get('content-type');
    let data;
    
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    // Check if the response is successful
    if (!response.ok) {
      throw new Error(
        typeof data === 'object' && data.detail 
          ? data.detail 
          : `API request failed with status ${response.status}`
      );
    }

    return data;
  } catch (error) {
    console.error('Auth fetch error:', error);
    throw error;
  }
}

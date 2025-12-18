/**
 * Helper functions for better-auth authentication
 * These are server-side helper functions for working with better-auth
 */
import { getAuth } from "@/lib/auth";

/**
 * Get authentication token from better-auth session
 * Note: This is a placeholder for future server-side token retrieval
 * Client-side token retrieval uses the useSession hook from auth-client.ts
 */
export async function getAuthToken(): Promise<string | null> {
  try {
    // Get the connected auth instance and session
    const auth = await getAuth();
    const session = await auth.api.getSession();
    return session?.session?.token || null;
  } catch (error) {
    console.error("Error getting auth token:", error);
    return null;
  }
}

/**
 * Get current user information from session
 * Returns user profile data including id, email, and name
 */
export async function getUserInfo() {
  try {
    const auth = await getAuth();
    const session = await auth.api.getSession();
    return session?.user || null;
  } catch (error) {
    console.error("Error getting user info:", error);
    return null;
  }
}

/**
 * Check if user has a specific role
 * @param role The role to check
 * @returns True if the user has the role, false otherwise
 */
export async function hasRole(role: string): Promise<boolean> {
  try {
    const user = await getUserInfo();
    if (!user) return false;

    // Check if the user has the role (assuming role is stored as a field)
    // Adjust based on your actual user schema
    return (user as any).role === role;
  } catch (error) {
    console.error("Error checking role:", error);
    return false;
  }
}

/**
 * Check if user is authenticated
 * @returns True if the user is authenticated, false otherwise
 */
export async function isAuthenticated(): Promise<boolean> {
  try {
    const auth = await getAuth();
    const session = await auth.api.getSession();
    return !!session?.user;
  } catch (error) {
    console.error("Error checking authentication:", error);
    return false;
  }
}

/**
 * Check if user is authorized (authenticated + optional role check)
 * @param requiredRole Optional role to check
 * @returns True if the user is authenticated and has the required role (if specified)
 */
export async function isAuthorized(requiredRole?: string): Promise<boolean> {
  const authenticated = await isAuthenticated();

  if (!authenticated) return false;
  if (!requiredRole) return true;

  return await hasRole(requiredRole);
}

/**
 * Helper functions for Clerk authentication in different contexts
 * Note: These functions can only be used in Server Components or API routes
 */
import { auth } from "@clerk/nextjs/server";
import { currentUser } from "@clerk/nextjs/server";

/**
 * Get the current auth token for API requests
 * @returns The authentication token from Clerk
 */
export async function getAuthToken(): Promise<string | null> {
  try {
    // Get the auth session
    const session = await auth();
    // Return the session token if available
    return session.sessionId || null;
  } catch (error) {
    console.error("Error getting auth token:", error);
    return null;
  }
}

/**
 * Get the current user from Clerk
 * @returns The current user information
 */
export async function getUserInfo() {
  try {
    const user = await currentUser();
    return user;
  } catch (error) {
    console.error("Error getting user info:", error);
    return null;
  }
}

/**
 * Check if the user has a specific role
 * @param role The role to check
 * @returns True if the user has the role, false otherwise
 */
export async function hasRole(role: string): Promise<boolean> {
  try {
    const user = await currentUser();
    if (!user) return false;
    
    // Check if the user has the role in their public metadata
    const userRoles = user.publicMetadata.roles as string[] || [];
    return Array.isArray(userRoles) && userRoles.includes(role);
  } catch (error) {
    console.error("Error checking role:", error);
    return false;
  }
}

/**
 * Check if a user is authenticated - use this instead of protect()
 * @returns True if the user is authenticated, false otherwise
 */
export async function isAuthenticated(): Promise<boolean> {
  const session = await auth();
  return !!session.userId;
}

/**
 * Check if a user is authenticated and has the required role
 * @param role The role to check
 * @returns True if the user is authenticated and has the role, false otherwise
 */
export async function isAuthorized(role: string): Promise<boolean> {
  const isUserAuthenticated = await isAuthenticated();
  if (!isUserAuthenticated) return false;
  
  return await hasRole(role);
}

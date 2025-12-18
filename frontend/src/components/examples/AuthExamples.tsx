/**
 * Examples of how to use authentication in different contexts
 * 
 * This file is for demonstration purposes only.
 */

// CLIENT COMPONENT EXAMPLE
"use client";

import { useEffect, useState } from "react";
import { useAuthFetch } from "@/hooks/useAuthFetch";
import { useSession } from "@/lib/auth-client";

export function ClientComponentExample() {
  const { data: session } = useSession();
  const { authFetch, loading, error } = useAuthFetch();
  const [data, setData] = useState<unknown>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        // Use the authFetch hook in client components
        const result = await authFetch("/api/some-protected-endpoint");
        setData(result);
      } catch (err) {
        console.error("Failed to fetch data:", err);
      }
    }

    if (session?.user) {
      fetchData();
    }
  }, [session?.user, authFetch]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!session?.user) return <div>Please sign in</div>;

  return (
    <div>
      <h2>Client Component Example</h2>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}

// SERVER COMPONENT EXAMPLE
// This would be in a separate file with no "use client" directive
/*
import { getAuthToken, getUserInfo, isAuthenticated, isAuthorized } from "@/lib/clerk-helpers";

export async function ServerComponentExample() {
  // Check if user is authenticated
  const isUserAuthenticated = await isAuthenticated();
  if (!isUserAuthenticated) {
    return <div>Please sign in to view this content</div>;
  }
  
  // In server components, use the clerk-helpers directly
  const token = await getAuthToken();
  const user = await getUserInfo();
  
  // Check if user has admin role for certain protected content
  const isAdmin = await isAuthorized('admin');
  
  let data = null;
  
  if (token) {
    // Make an authenticated fetch request
    const response = await fetch("https://your-api.com/some-endpoint", {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    
    if (response.ok) {
      data = await response.json();
    }
  }
  
  return (
    <div>
      <h2>Server Component Example</h2>
      {user ? (
        <>
          <p>Hello, {user.firstName}!</p>
          <pre>{JSON.stringify(data, null, 2)}</pre>
          
          {isAdmin && (
            <div>
              <h3>Admin Section</h3>
              <p>This content is only visible to admins</p>
            </div>
          )}
        </>
      ) : (
        <p>Please sign in</p>
      )}
    </div>
  );
}
*/

// API ROUTE EXAMPLE
// This would be in a separate file in the app/api directory
/*
import { NextRequest, NextResponse } from "next/server";
import { getAuthToken, isAuthenticated, isAuthorized } from "@/lib/clerk-helpers";

export async function GET(req: NextRequest) {
  // Check if the user is authenticated
  const isUserAuthenticated = await isAuthenticated();
  if (!isUserAuthenticated) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401 }
    );
  }
  
  // For endpoints requiring specific roles
  const isAdmin = await isAuthorized('admin');
  if (!isAdmin && req.nextUrl.pathname.includes('/admin')) {
    return NextResponse.json(
      { error: "Forbidden - Admin access required" },
      { status: 403 }
    );
  }
  
  // Get the token for making authenticated requests
  const token = await getAuthToken();
  
  // Make an authenticated request to another API if needed
  const response = await fetch("https://external-api.com/data", {
    headers: {
      Authorization: `Bearer ${token || ''}`
    }
  });
  
  const data = await response.json();
  
  return NextResponse.json({
    data,
    user: {
      isAdmin
    }
  });
}
*/

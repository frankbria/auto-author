// app/page.tsx
'use client';

import { SignedIn, SignedOut, SignInButton, SignUpButton, SignOutButton, useUser } from '@clerk/nextjs';
import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function Home() {
  const { isLoaded, isSignedIn } = useUser();
  const [isAuthReady, setIsAuthReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isLoaded) {
      setIsAuthReady(true);
    }
  }, [isLoaded]);

  // Show loading state while Clerk is initializing
  if (!isAuthReady) {
    return (
      <div className="flex flex-col items-center justify-center text-center p-6 min-h-screen">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
          <p className="text-zinc-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Show any authentication errors
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center text-center p-6 min-h-screen">
        <div className="bg-red-900/20 border border-red-700 text-red-400 p-4 rounded-lg mb-6 max-w-md">
          <p>Authentication Error: {error}</p>
        </div>
        <button 
          onClick={() => setError(null)} 
          className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-md"
        >
          Dismiss
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center text-center p-6 min-h-screen">
      <SignedOut>
        <div className="space-y-6">
          <h1 className="text-4xl font-extrabold text-white tracking-tight sm:text-5xl">
            Welcome to <span className="text-indigo-500">Auto Author</span>
          </h1>
          <p className="text-zinc-400 max-w-xl mx-auto">
            Your AI-powered assistant for creating nonfiction books—chapter by chapter, interview style.
          </p>
          <div className="space-x-4">
            <SignInButton mode="modal" fallbackRedirectUrl="/dashboard">
              <button className="px-6 py-3 text-white font-semibold bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-md transition">
                Sign In
              </button>
            </SignInButton>
            <SignUpButton mode="modal" fallbackRedirectUrl="/dashboard">
              <button className="px-6 py-3 text-white font-semibold bg-zinc-700 hover:bg-zinc-600 rounded-lg shadow-md transition">
                Sign Up
              </button>
            </SignUpButton>
          </div>
        </div>
      </SignedOut>

      <SignedIn>
        <div className="space-y-6">
          <h1 className="text-4xl font-bold text-white">Welcome Back 👋</h1>
          <p className="text-zinc-400 mb-6">Continue working on your book projects.</p>
          <div className="space-x-4">
            <Link href="/dashboard">
              <button className="px-6 py-3 text-white font-semibold bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-md transition">
                Go to Dashboard
              </button>
            </Link>
            <SignOutButton>
              <button className="px-6 py-3 text-white font-semibold bg-zinc-700 hover:bg-zinc-600 rounded-lg shadow-md transition">
                Sign Out
              </button>
            </SignOutButton>
          </div>
        </div>
      </SignedIn>
    </div>
  );
}

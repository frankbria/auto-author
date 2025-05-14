'use client';

import { SignUp } from '@clerk/nextjs';
import { dark } from '@clerk/themes';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function SignUpPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Handle sign up error
  const handleSignUpError = (errorMessage: string) => {
    setError(errorMessage);
    setIsLoading(false);
    console.error('Sign up error:', errorMessage);
  };

  return (
    <div className="flex flex-col justify-center items-center min-h-screen p-4">
      {isLoading && (
        <div className="fixed inset-0 flex items-center justify-center bg-zinc-900/70 z-50">
          <div className="bg-zinc-800 p-6 rounded-lg shadow-xl flex flex-col items-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500 mb-4"></div>
            <p className="text-zinc-300">Redirecting to dashboard...</p>
          </div>
        </div>
      )}
      
      {error && (
        <div className="mb-4 w-full max-w-md bg-red-900/30 border border-red-700 text-red-400 px-4 py-3 rounded-md">
          <p>{error}</p>
        </div>
      )}
      
      <SignUp 
        appearance={{ 
          baseTheme: dark,
          elements: {
            card: 'bg-zinc-800 border border-zinc-700 shadow-xl',
            headerTitle: 'text-zinc-100',
            headerSubtitle: 'text-zinc-400',
            formButtonPrimary: 'bg-indigo-600 hover:bg-indigo-700',
            formFieldLabel: 'text-zinc-300',
            formFieldInput: 'bg-zinc-900 border-zinc-700 text-zinc-100',
            footerActionLink: 'text-indigo-400 hover:text-indigo-300',
          },
        }}
        routing="path"
        path="/sign-up"
        signInUrl="/sign-in"
        redirectUrl="/dashboard"
        afterSignUpUrl="/dashboard"
        // Removed invalid prop 'onSignUpFailed'
      />
    </div>
  );
}

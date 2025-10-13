// app/layout.tsx

import { ClerkProvider } from '@clerk/nextjs';
import { dark } from '@clerk/themes';
import { Inter } from 'next/font/google';
import './globals.css';
import { Toaster } from '@/components/ui/toaster';
import { SonnerProvider } from '@/components/ui/sonner';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { WebVitalsInit } from '@/components/performance/WebVitalsInit';

const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: 'Auto Author',
  description: 'AI-powered nonfiction book writing assistant',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider 
      appearance={{ baseTheme: dark }}
      // Extend session duration for development
      publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
    >
      <html lang="en" className="scroll-smooth">
        <body className={`${inter.className} bg-zinc-950 text-zinc-100 min-h-screen`}>
          <ErrorBoundary
            fallback={
              <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center p-4">
                <div className="text-center">
                  <h1 className="text-2xl font-bold text-red-400 mb-4">Something went wrong</h1>
                  <p className="text-zinc-400 mb-4">An unexpected error occurred. Please refresh the page.</p>
                  <button 
                    onClick={() => window.location.reload()} 
                    className="bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded"
                  >
                    Refresh Page
                  </button>
                </div>
              </div>
            }
          >
            <WebVitalsInit />
            <main className="flex flex-col min-h-screen">
              {/* Placeholder for future header/sidebar */}
              <div className="flex-1 flex flex-col">{children}</div>
              <Toaster />
              <SonnerProvider />
            </main>
          </ErrorBoundary>
        </body>
      </html>
    </ClerkProvider>
  );
}

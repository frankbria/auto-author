// app/layout.tsx

import { Nunito_Sans } from 'next/font/google';
import './globals.css';
import { Toaster } from '@/components/ui/toaster';
import { Toaster as SonnerToaster } from '@/components/ui/sonner';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { WebVitalsInit } from '@/components/performance/WebVitalsInit';
import { RefreshButton } from '@/components/ui/refresh-button';
const nunitoSans = Nunito_Sans({ subsets: ['latin'] });

export const metadata = {
  title: 'Auto Author',
  description: 'AI-powered nonfiction book writing assistant',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className={`${nunitoSans.className} bg-gray-950 text-gray-100 min-h-screen`}>
        <ErrorBoundary
          fallback={
            <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center p-4">
              <div className="text-center">
                <h1 className="text-2xl font-bold text-red-400 mb-4">Something went wrong</h1>
                <p className="text-gray-400 mb-4">An unexpected error occurred. Please refresh the page.</p>
                <RefreshButton />
              </div>
            </div>
          }
        >
          <WebVitalsInit />
          <main className="flex flex-col min-h-screen">
            {/* Placeholder for future header/sidebar */}
            <div className="flex-1 flex flex-col">{children}</div>
            <Toaster />
            <SonnerToaster />
          </main>
        </ErrorBoundary>
      </body>
    </html>
  );
}

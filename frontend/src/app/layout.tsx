// app/layout.tsx

import { Nunito_Sans } from 'next/font/google';
import { headers } from 'next/headers';
import './globals.css';
import { Toaster as SonnerToaster } from '@/components/ui/sonner';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { WebVitalsInit } from '@/components/performance/WebVitalsInit';
import { RefreshButton } from '@/components/ui/refresh-button';
import { ThemeProvider } from 'next-themes';

const nunitoSans = Nunito_Sans({ subsets: ['latin'] });

export const metadata = {
  title: 'Auto Author',
  description: 'AI-powered nonfiction book writing assistant',
};

// ponytail: no maximum-scale — clamping zoom is a WCAG 1.4.4 anti-pattern. viewport-fit=cover
// lets content use the full screen on notched devices.
export const viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover' as const,
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Per-request CSP nonce from middleware (#190). next-themes injects an
  // inline theme script that must carry it. Reading headers() also forces
  // dynamic rendering, which nonce-based CSP requires.
  const nonce = (await headers()).get('x-nonce') ?? undefined;
  return (
    <html lang="en" className="scroll-smooth" suppressHydrationWarning>
      {/* Token classes (not hardcoded gray-950) so the stored theme preference
          actually flips light/dark; defaultTheme="dark" keeps the shipped look. */}
      <body className={`${nunitoSans.className} bg-background text-foreground min-h-screen`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
          nonce={nonce}
        >
          <ErrorBoundary
            fallback={
              // Keep the skip-link target / main landmark even in the error state.
              <main id="main-content" tabIndex={-1} className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center p-4">
                <div className="text-center">
                  <h1 className="text-2xl font-bold text-red-400 mb-4">Something went wrong</h1>
                  <p className="text-gray-400 mb-4">An unexpected error occurred. Please refresh the page.</p>
                  <RefreshButton />
                </div>
              </main>
            }
          >
            <WebVitalsInit />
            {/* Skip link: first focusable element, visually hidden until focused.
                Targets the per-page <main id="main-content"> landmark. */}
            <a
              href="#main-content"
              className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground focus:shadow-lg"
            >
              Skip to main content
            </a>
            {/* Layout wrapper only — the semantic <main> landmark lives in each
                page/layout so banner/contentinfo can be top-level siblings. */}
            <div className="flex flex-col min-h-screen">
              <div className="flex-1 flex flex-col">{children}</div>
              <SonnerToaster />
            </div>
          </ErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  );
}

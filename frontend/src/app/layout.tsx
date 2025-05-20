// app/layout.tsx

import { ClerkProvider } from '@clerk/nextjs';
import { dark } from '@clerk/themes';
import { Inter } from 'next/font/google';
import './globals.css';
import { Toaster } from '@/components/ui/toaster';
import { SonnerProvider } from '@/components/ui/sonner';

const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: 'Auto Author',
  description: 'AI-powered nonfiction book writing assistant',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider appearance={{ baseTheme: dark }}>
      <html lang="en" className="scroll-smooth">
        <body className={`${inter.className} bg-zinc-950 text-zinc-100 min-h-screen`}>
          <main className="flex flex-col min-h-screen">
            {/* Placeholder for future header/sidebar */}
            <div className="flex-1 flex flex-col">{children}</div>
            <Toaster />
            <SonnerProvider />
          </main>
        </body>
      </html>
    </ClerkProvider>
  );
}

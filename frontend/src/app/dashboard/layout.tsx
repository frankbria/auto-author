'use client';

import { UserButton } from '@/components/ui/user-button';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Navigation items with active state detection
  const navItems = [
    { name: 'Dashboard', href: '/dashboard', active: pathname === '/dashboard' },
    { name: 'Settings', href: '/dashboard/settings', active: pathname === '/dashboard/settings' },
    { name: 'Help', href: '/dashboard/help', active: pathname === '/dashboard/help' },
  ];

  return (
    <ProtectedRoute>
      <div className="flex flex-col min-h-screen">
        {/* Header/Navigation */}
        {/* Theme-token surfaces so the stored theme preference (#64) is visible */}
        <header className="bg-card border-b border-border py-4 px-6 sticky top-0 z-50">
          <div className="container mx-auto flex justify-between items-center">
            <Link href="/dashboard" className="text-2xl font-bold text-indigo-500">Auto Author</Link>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center gap-4">
              <nav aria-label="Main navigation">
                <ul className="flex items-center gap-6">
                  {navItems.map((item) => (
                    <li key={item.name}>
                      <Link
                        href={item.href}
                        className={`${
                          item.active
                            ? 'text-primary font-medium'
                            : 'text-muted-foreground hover:text-primary'
                        } transition-colors`}
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
              <UserButton />
            </div>

            {/* Mobile Navigation */}
            <div className="md:hidden flex items-center gap-4">
              <UserButton />
              {/* The Radix sheet gives the drawer its dialog role, focus trap, Escape and aria-expanded (#837) */}
              <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
                <SheetTrigger asChild>
                  <button
                    className="flex items-center justify-center min-h-11 min-w-11 text-muted-foreground hover:text-foreground transition-colors"
                    aria-label="Toggle mobile menu"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                    </svg>
                  </button>
                </SheetTrigger>
                <SheetContent side="right" className="w-64 bg-card" aria-describedby={undefined}>
                  <SheetHeader className="px-6 pt-6 pb-2">
                    <SheetTitle className="text-lg">Menu</SheetTitle>
                  </SheetHeader>
                  <nav aria-label="Mobile navigation" className="px-6">
                    <ul className="space-y-4">
                      {navItems.map((item) => (
                        <li key={item.name}>
                          <Link
                            href={item.href}
                            onClick={() => setIsMobileMenuOpen(false)}
                            className={`block py-3 px-4 rounded-lg transition-colors ${
                              item.active
                                ? 'bg-primary text-primary-foreground font-medium'
                                : 'text-muted-foreground hover:bg-accent hover:text-primary'
                            }`}
                          >
                            {item.name}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </nav>
                </SheetContent>
              </Sheet>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main id="main-content" tabIndex={-1} className="flex-1 bg-background">
          {children}
        </main>

        {/* Footer */}
        <footer className="bg-card border-t border-border py-4 px-6">
          <div className="container mx-auto text-center text-muted-foreground text-sm">
            <p>© 2025 Noatak Enterprises, LLC, dba Auto Author. All rights reserved.</p>
          </div>
        </footer>
      </div>
    </ProtectedRoute>
  );
}

'use client';

import { UserButton } from '@clerk/nextjs';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

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

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };
  return (
    <ProtectedRoute>
      <div className="flex flex-col min-h-screen">
        {/* Header/Navigation */}
        <header className="bg-zinc-900 border-b border-zinc-800 py-4 px-6 sticky top-0 z-50">
          <div className="container mx-auto flex justify-between items-center">
            <Link href="/dashboard" className="text-2xl font-bold text-indigo-500">Auto Author</Link>
            
            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center gap-4">
              <nav>
                <ul className="flex items-center gap-6">
                  {navItems.map((item) => (
                    <li key={item.name}>
                      <Link 
                        href={item.href} 
                        className={`${
                          item.active 
                            ? 'text-indigo-400 font-medium' 
                            : 'text-zinc-400 hover:text-indigo-400'
                        } transition-colors`}
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
              <UserButton afterSignOutUrl="/" />
            </div>

            {/* Mobile Navigation */}
            <div className="md:hidden flex items-center gap-4">
              <UserButton afterSignOutUrl="/" />
              <button
                onClick={toggleMobileMenu}
                className="text-zinc-400 hover:text-zinc-100 transition-colors p-2"
                aria-label="Toggle mobile menu"
              >
                <svg 
                  className="w-6 h-6" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  {isMobileMenuOpen ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  )}
                </svg>
              </button>
            </div>
          </div>

          {/* Mobile Menu Drawer */}
          {isMobileMenuOpen && (
            <>
              {/* Backdrop */}
              <div 
                className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
                onClick={closeMobileMenu}
              />
              
              {/* Menu Panel */}
              <div className="fixed top-0 right-0 h-full w-64 bg-zinc-900 border-l border-zinc-800 z-50 md:hidden transform transition-transform duration-300 ease-in-out">
                <div className="p-6">
                  <div className="flex justify-between items-center mb-8">
                    <h2 className="text-lg font-semibold text-zinc-100">Menu</h2>
                    <button
                      onClick={closeMobileMenu}
                      className="text-zinc-400 hover:text-zinc-100 transition-colors p-1"
                      aria-label="Close menu"
                    >
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  
                  <nav>
                    <ul className="space-y-4">
                      {navItems.map((item) => (
                        <li key={item.name}>
                          <Link 
                            href={item.href}
                            onClick={closeMobileMenu}
                            className={`block py-3 px-4 rounded-lg transition-colors ${
                              item.active 
                                ? 'bg-indigo-600 text-white font-medium' 
                                : 'text-zinc-300 hover:bg-zinc-800 hover:text-indigo-400'
                            }`}
                          >
                            {item.name}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </nav>
                </div>
              </div>
            </>
          )}
        </header>

        {/* Main Content */}
        <div className="flex-1 bg-zinc-950">
          {children}
        </div>

        {/* Footer */}
        <footer className="bg-zinc-900 border-t border-zinc-800 py-4 px-6">
          <div className="container mx-auto text-center text-zinc-500 text-sm">
            <p>© 2025 Noatak Enterprises, LLC, dba Auto Author. All rights reserved.</p>
          </div>
        </footer>
      </div>
    </ProtectedRoute>
  );
}

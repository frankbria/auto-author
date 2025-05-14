'use client';

import { UserButton } from '@clerk/nextjs';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  
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
        <header className="bg-zinc-900 border-b border-zinc-800 py-4 px-6 sticky top-0 z-10">
          <div className="container mx-auto flex justify-between items-center">
            <Link href="/dashboard" className="text-2xl font-bold text-indigo-500">Auto Author</Link>
            <div className="flex items-center gap-4">
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
                        }`}
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
              <UserButton afterSignOutUrl="/" />
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="flex-1 bg-zinc-950">
          {children}
        </div>

        {/* Footer */}
        <footer className="bg-zinc-900 border-t border-zinc-800 py-4 px-6">
          <div className="container mx-auto text-center text-zinc-500 text-sm">
            <p>© 2025 Auto Author. All rights reserved.</p>
          </div>
        </footer>
      </div>
    </ProtectedRoute>
  );
}

'use client';

import Link from 'next/link';
import { useSession } from '@/lib/auth-client';
import { signOutOrNotify } from '@/lib/sign-out';

// The public pages' header: the name, Pricing, and the way in. A signed-in
// visitor gets "Go to dashboard" and Sign out instead of the sign-up call to action. Until
// the session is known it shows the signed-out links, so a visitor never waits
// on a spinner to read the page (#584's loader is gone with the old home page).
export default function MarketingHeader() {
  const { data: session } = useSession();
  const signedIn = Boolean(session?.user);

  return (
    <header className="w-full border-b border-border">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-4">
        <Link href="/" className="text-lg font-bold text-foreground">
          Auto Author
        </Link>
        <nav aria-label="Main" className="flex items-center gap-4 text-sm">
          <Link href="/pricing" className="text-muted-foreground hover:text-foreground hover:underline">
            Pricing
          </Link>
          {signedIn ? (
            <>
              <button
                type="button"
                onClick={() => void signOutOrNotify()}
                className="text-muted-foreground hover:text-foreground hover:underline"
              >
                Sign out
              </button>
              <Link
                href="/dashboard"
                className="rounded-md bg-primary px-4 py-2 font-semibold text-primary-foreground hover:bg-primary/90"
              >
                Go to dashboard
              </Link>
            </>
          ) : (
            <>
              <Link href="/auth/sign-in" className="text-muted-foreground hover:text-foreground hover:underline">
                Sign in
              </Link>
              <Link
                href="/auth/sign-up"
                data-goatcounter-click="cta-header-trial"
                className="rounded-md bg-primary px-4 py-2 font-semibold text-primary-foreground hover:bg-primary/90"
              >
                Start free trial
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

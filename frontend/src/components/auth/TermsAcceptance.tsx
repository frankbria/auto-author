'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { acceptTerms } from '@/lib/auth-client';
import { TERMS_LAST_UPDATED } from '@/lib/constants/legal';
import { signOutOrNotify } from '@/lib/sign-out';

interface TermsAcceptanceProps {
  /** Called once the acceptance is recorded; reloads the session. */
  onAccepted: () => unknown;
}

/**
 * Shown in place of a protected page to an account whose recorded Terms
 * version is older than TERMS_VERSION, or missing (#961). Asked once: the
 * server records the acceptance, and the reloaded session no longer needs it.
 */
export function TermsAcceptance({ onAccepted }: TermsAcceptanceProps) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);

  async function accept() {
    setSaving(true);
    setFailed(false);
    const recorded = await acceptTerms().then(
      ({ error }) => !error,
      () => false
    );
    if (recorded) {
      await onAccepted();
    } else {
      setFailed(true);
    }
    setSaving(false);
  }

  async function signOut() {
    if (await signOutOrNotify()) router.push('/');
  }

  return (
    <main
      id="main-content"
      tabIndex={-1}
      className="flex min-h-screen items-center justify-center bg-background px-4 py-10"
    >
      <section
        aria-labelledby="terms-acceptance-heading"
        className="w-full max-w-lg rounded-lg border border-border bg-card p-6 shadow-sm"
      >
        <h1 id="terms-acceptance-heading" className="text-2xl font-bold text-foreground">
          Please accept the Terms of Service
        </h1>
        <p className="mt-3 text-muted-foreground">
          Our Terms of Service were last updated on {TERMS_LAST_UPDATED}. To keep
          using Auto Author, please read them and accept.
        </p>
        <p className="mt-3">
          <Link
            href="/terms"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary underline underline-offset-4"
          >
            Read the Terms of Service (opens in a new tab)
          </Link>
        </p>
        <p role="alert" className="mt-4 text-sm text-destructive empty:hidden">
          {failed
            ? 'We could not record your acceptance. Check your connection and try again.'
            : ''}
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <Button onClick={accept} busy={saving} className="min-h-11">
            {saving ? 'Accepting…' : 'I accept the Terms of Service'}
          </Button>
          <Button variant="outline" onClick={signOut} disabled={saving} className="min-h-11">
            Sign out
          </Button>
        </div>
      </section>
    </main>
  );
}

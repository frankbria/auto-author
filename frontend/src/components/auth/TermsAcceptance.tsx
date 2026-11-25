'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { acceptTerms } from '@/lib/auth-client';
import { TERMS_LAST_UPDATED } from '@/lib/constants/legal';
import { signOutOrNotify } from '@/lib/sign-out';
import { openTermsExits } from '@/lib/terms-exits';

const NOT_RECORDED =
  'We could not record your acceptance. Check your connection and try again.';
const TERMS_CHANGED =
  'The Terms of Service changed while this page was open. Reload the page to read the current version.';

interface TermsAcceptanceProps {
  /** The signed-in account, for which the exit links open Settings and Profile. */
  userId: string;
  /** Called once the acceptance is recorded. */
  onAccepted: () => unknown;
}

/**
 * Shown in place of a protected page to an account whose recorded Terms
 * version is older than TERMS_VERSION, or missing (#961). Asked once: the
 * server records the acceptance, and the reloaded session no longer needs it.
 */
export function TermsAcceptance({ userId, onAccepted }: TermsAcceptanceProps) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState('');
  const acceptRef = useRef<HTMLButtonElement>(null);

  async function accept() {
    setSaving(true);
    setProblem('');
    const status = await acceptTerms().then(
      ({ error }) => (error ? error.status : 200),
      () => 0
    );
    setSaving(false);
    if (status === 200) {
      onAccepted();
    } else {
      setProblem(status === 409 ? TERMS_CHANGED : NOT_RECORDED);
      // Disabling the button while saving dropped focus to the page.
      requestAnimationFrame(() => acceptRef.current?.focus());
    }
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
        <p className="mt-3 text-muted-foreground">
          Not ready to accept? You can still{' '}
          <Link
            href="/dashboard/settings?tab=billing"
            onClick={() => openTermsExits(userId)}
            className="text-primary underline underline-offset-4"
          >
            cancel your subscription
          </Link>{' '}
          or{' '}
          <Link
            href="/profile"
            onClick={() => openTermsExits(userId)}
            className="text-primary underline underline-offset-4"
          >
            download your data or delete your account
          </Link>
          .
        </p>
        {/* Always rendered, so the live region exists before it has text to announce. */}
        <p role="alert" className={`text-sm text-destructive ${problem ? 'mt-4' : ''}`}>
          {problem}
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <Button
            ref={acceptRef}
            onClick={accept}
            busy={saving}
            // Wraps at 200% text instead of overflowing a narrow card (WCAG 1.4.4).
            className="h-auto min-h-11 whitespace-normal"
          >
            {saving ? 'Accepting…' : 'I accept the Terms of Service'}
          </Button>
          <Button
            variant="outline"
            onClick={signOut}
            disabled={saving}
            className="h-auto min-h-11 whitespace-normal"
          >
            Sign out
          </Button>
        </div>
      </section>
    </main>
  );
}

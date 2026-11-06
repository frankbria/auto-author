'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import {
  useBillingApi,
  type PlanQuota,
  type PlanQuotas,
  type RenewalDisclosure,
} from '@/hooks/useBillingApi';
import { toast } from '@/lib/toast';
import { navigateTo } from '@/lib/navigation';

interface BillingSettingsFormProps {
  plan?: string;
  /** True when the user has a Stripe customer — the portal's exact backend gate. */
  hasBillingAccount?: boolean;
}

const limit = (n: number | null) => (n === null ? 'unlimited' : String(n));

const EXPORT_FORMATS = 'PDF, DOCX, EPUB and Markdown';

/** "50 AI generations per day (500 per month)", or the one window that is set. */
function windows(q: PlanQuota): string {
  if (q.daily === null && q.monthly === null) return 'unlimited AI generations';
  if (q.monthly === null) return `${limit(q.daily)} AI generations per day`;
  if (q.daily === null) return `${limit(q.monthly)} AI generations per month`;
  return `${q.daily} AI generations per day (${q.monthly} per month)`;
}

/** What Pro includes, in one clause list. Read from the backend (#766). */
function proIncludes(q: PlanQuota): string {
  const parts = [windows(q)];
  if (q.draft_chapters == null) parts.push('AI drafts for every chapter');
  if (q.export !== false) parts.push(`export to ${EXPORT_FORMATS}`);
  return parts.length > 1
    ? `${parts.slice(0, -1).join(', ')} and ${parts[parts.length - 1]}`
    : parts[0];
}

/**
 * Free is a trial for testing Auto Author on one chapter, not a plan to write a
 * book on (owner decision 2026-10-28). Say so, with the backend's numbers.
 */
function freeTrialCopy(q: PlanQuotas): string {
  const free = q.free;
  const sentences = [
    "The free trial is for testing Auto Author on your own material: a summary, a table of contents, and one chapter's interview and draft.",
  ];
  const limits: string[] = [];
  if (free.total != null) limits.push(`${free.total} AI generations in total, which don't reset`);
  if (free.draft_chapters != null) {
    limits.push(
      `an AI draft of ${free.draft_chapters === 1 ? 'one chapter' : `${free.draft_chapters} chapters`}`
    );
  }
  if (limits.length) sentences.push(`It includes ${limits.join(' and ')}.`);
  if (free.export === false) sentences.push('Exporting your book is part of Pro.');
  sentences.push(`Pro includes ${proIncludes(q.pro)}.`);
  return sentences.join(' ');
}

/**
 * Billing tab: current plan + Stripe checkout entry point (issue #221)
 * + billing-portal access for paid users (issue #222).
 * Self-serves its own actions, so it doesn't go through the shared
 * preferences Save button (mirrors SecuritySettingsForm's contract).
 */
export default function BillingSettingsForm({ plan, hasBillingAccount }: BillingSettingsFormProps) {
  const { startCheckout, openBillingPortal, getPlanQuotas, getRenewalDisclosure } =
    useBillingApi();
  const [quotas, setQuotas] = useState<PlanQuotas | null>(null);
  const [disclosure, setDisclosure] = useState<RenewalDisclosure | null>(null);
  const [disclosureFailed, setDisclosureFailed] = useState(false);
  const [disclosureAttempt, setDisclosureAttempt] = useState(0);
  const [agreed, setAgreed] = useState(false);
  const [isRedirecting, setIsRedirecting] = useState(false);
  const isPro = plan === 'pro';

  // The renewal terms come from the backend (priced from the Stripe Price itself)
  // and must be shown and agreed to before checkout can start (#770).
  useEffect(() => {
    if (isPro) return;
    let active = true;
    getRenewalDisclosure()
      .then((d) => active && setDisclosure(d))
      .catch(() => active && setDisclosureFailed(true));
    return () => {
      active = false;
    };
  }, [getRenewalDisclosure, isPro, disclosureAttempt]);

  const retryDisclosure = () => {
    setDisclosureFailed(false);
    setDisclosureAttempt((n) => n + 1);
  };

  // Limits are read from the backend so the copy can never drift from enforcement (#766).
  // On failure the card still renders; it just omits the numbers.
  useEffect(() => {
    let active = true;
    getPlanQuotas()
      .then((q) => active && setQuotas(q))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [getPlanQuotas]);

  const handleUpgrade = async () => {
    if (!disclosure || !agreed) return;
    setIsRedirecting(true);
    try {
      const { url } = await startCheckout('pro', disclosure.sha256);
      navigateTo(url);
    } catch (err) {
      toast({
        title: 'Could not start checkout',
        description: err instanceof Error ? err.message : 'Something went wrong. Please try again.',
        variant: 'destructive',
      });
      setIsRedirecting(false);
      // If the terms changed underneath us (backend 409), show the new ones and
      // ask again: agreeing to the old text is not consent to the new.
      const fresh = await getRenewalDisclosure().catch(() => null);
      if (fresh && fresh.sha256 !== disclosure.sha256) {
        setDisclosure(fresh);
        setAgreed(false);
      }
    }
  };

  const handleManageBilling = async () => {
    setIsRedirecting(true);
    try {
      const { url } = await openBillingPortal();
      navigateTo(url);
    } catch (err) {
      toast({
        title: 'Could not open billing portal',
        description: err instanceof Error ? err.message : 'Something went wrong. Please try again.',
        variant: 'destructive',
      });
      setIsRedirecting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Billing</CardTitle>
        <CardDescription>Manage your subscription plan</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isPro ? (
          <div className="space-y-1">
            <p className="font-medium">You&apos;re on the Pro plan</p>
            <p className="text-sm text-muted-foreground">
              Thanks for supporting Auto Author.
              {quotas && ` Your plan includes ${proIncludes(quotas.pro)}.`}
            </p>
          </div>
        ) : (
          <>
            <div className="space-y-1">
              <p className="font-medium">
                {plan === 'restricted' ? 'Your subscription is inactive' : 'Free trial'}
              </p>
              <p className="text-sm text-muted-foreground">
                {plan === 'restricted'
                  ? 'Fix your payment method below, or start a new upgrade to restore full access.'
                  : quotas
                    ? freeTrialCopy(quotas)
                    : 'The free trial lets you test Auto Author on one chapter. Upgrade to Pro to write and export your whole book.'}
              </p>
            </div>
            <div className="space-y-3 rounded-md border p-4">
              {disclosure ? (
                <>
                  <p id="renewal-disclosure" className="text-sm font-medium text-foreground">
                    {disclosure.text}
                  </p>
                  <div className="flex items-start gap-2">
                    <Checkbox
                      id="renewal-consent"
                      checked={agreed}
                      onCheckedChange={(v) => setAgreed(v === true)}
                      aria-describedby="renewal-disclosure"
                      className="mt-0.5"
                    />
                    <Label htmlFor="renewal-consent" className="block leading-snug">
                      I agree to these automatic renewal terms and the{' '}
                      <Link
                        href="/terms"
                        className="text-primary underline underline-offset-4"
                        target="_blank"
                      >
                        Terms of Service
                      </Link>
                      .
                    </Label>
                  </div>
                </>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground" role="status">
                    {disclosureFailed
                      ? 'Subscription terms are unavailable right now, so upgrading is paused.'
                      : 'Loading subscription terms…'}
                  </p>
                  {disclosureFailed && (
                    <Button variant="outline" size="sm" onClick={retryDisclosure}>
                      Try again
                    </Button>
                  )}
                </div>
              )}
              <Button
                onClick={handleUpgrade}
                disabled={isRedirecting || !disclosure || !agreed}
                busy={isRedirecting}
              >
                {isRedirecting ? 'Redirecting…' : 'Upgrade to Pro'}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Upgrades take effect after payment is confirmed by Stripe.
            </p>
          </>
        )}
        {/* Gated on the Stripe customer, not the plan — a lapsed (restricted) user
            still needs the portal to fix their payment method (backend allows it). */}
        {hasBillingAccount && (
          <>
            <Button
              variant={isPro ? 'default' : 'outline'}
              onClick={handleManageBilling}
              disabled={isRedirecting}
              busy={isRedirecting}
            >
              {isRedirecting ? 'Redirecting…' : 'Manage billing'}
            </Button>
            <p className="text-xs text-muted-foreground">
              Update your payment method, view invoices, or cancel in the Stripe billing portal.
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}

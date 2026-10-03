'use client';

import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useBillingApi, type PlanQuotas } from '@/hooks/useBillingApi';
import { toast } from '@/lib/toast';
import { navigateTo } from '@/lib/navigation';

interface BillingSettingsFormProps {
  plan?: string;
  /** True when the user has a Stripe customer — the portal's exact backend gate. */
  hasBillingAccount?: boolean;
}

const limit = (n: number | null) => (n === null ? 'unlimited' : String(n));

/**
 * Billing tab: current plan + Stripe checkout entry point (issue #221)
 * + billing-portal access for paid users (issue #222).
 * Self-serves its own actions, so it doesn't go through the shared
 * preferences Save button (mirrors SecuritySettingsForm's contract).
 */
export default function BillingSettingsForm({ plan, hasBillingAccount }: BillingSettingsFormProps) {
  const { startCheckout, openBillingPortal, getPlanQuotas } = useBillingApi();
  const [quotas, setQuotas] = useState<PlanQuotas | null>(null);
  const [isRedirecting, setIsRedirecting] = useState(false);
  const isPro = plan === 'pro';

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
    setIsRedirecting(true);
    try {
      const { url } = await startCheckout('pro');
      navigateTo(url);
    } catch (err) {
      toast({
        title: 'Could not start checkout',
        description: err instanceof Error ? err.message : 'Something went wrong. Please try again.',
        variant: 'destructive',
      });
      setIsRedirecting(false);
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
              {quotas &&
                ` Your plan includes ${limit(quotas.pro.daily)} AI generations per day (${limit(quotas.pro.monthly)} per month).`}
            </p>
          </div>
        ) : (
          <>
            <div className="space-y-1">
              <p className="font-medium">
                {plan === 'restricted' ? 'Your subscription is inactive' : 'Free plan'}
              </p>
              <p className="text-sm text-muted-foreground">
                {plan === 'restricted'
                  ? 'Fix your payment method below, or start a new upgrade to restore full access.'
                  : quotas
                    ? `Free: ${limit(quotas.free.daily)} AI generations per day (${limit(quotas.free.monthly)} per month). Pro: ${limit(quotas.pro.daily)} per day (${limit(quotas.pro.monthly)} per month).`
                    : 'Upgrade to Pro for a higher daily and monthly AI generation limit.'}
              </p>
            </div>
            <Button onClick={handleUpgrade} disabled={isRedirecting} busy={isRedirecting}>
              {isRedirecting ? 'Redirecting…' : 'Upgrade to Pro'}
            </Button>
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

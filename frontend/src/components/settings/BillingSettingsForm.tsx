'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useBillingApi } from '@/hooks/useBillingApi';
import { toast } from '@/lib/toast';

interface BillingSettingsFormProps {
  plan?: string;
  /** True when the user has a Stripe customer — the portal's exact backend gate. */
  hasBillingAccount?: boolean;
}

/**
 * Billing tab: current plan + Stripe checkout entry point (issue #221)
 * + billing-portal access for paid users (issue #222).
 * Self-serves its own actions, so it doesn't go through the shared
 * preferences Save button (mirrors SecuritySettingsForm's contract).
 */
export default function BillingSettingsForm({ plan, hasBillingAccount }: BillingSettingsFormProps) {
  const { startCheckout, openBillingPortal } = useBillingApi();
  const [isRedirecting, setIsRedirecting] = useState(false);
  const isPro = plan === 'pro';

  const handleUpgrade = async () => {
    setIsRedirecting(true);
    try {
      const { url } = await startCheckout('pro');
      window.location.assign(url);
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
      window.location.assign(url);
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
              Thanks for supporting Auto Author — you have full access to every feature.
            </p>
          </div>
        ) : (
          <>
            <div className="space-y-1">
              <p className="font-medium">Free plan</p>
              <p className="text-sm text-muted-foreground">
                Upgrade to Pro for full access to every AI writing feature.
              </p>
            </div>
            <Button onClick={handleUpgrade} disabled={isRedirecting}>
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

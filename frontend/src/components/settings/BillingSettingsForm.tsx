'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useBillingApi } from '@/hooks/useBillingApi';
import { toast } from '@/lib/toast';

interface BillingSettingsFormProps {
  plan?: string;
}

/**
 * Billing tab: current plan + Stripe checkout entry point (issue #221).
 * Self-serves its own action, so it doesn't go through the shared
 * preferences Save button (mirrors SecuritySettingsForm's contract).
 */
export default function BillingSettingsForm({ plan }: BillingSettingsFormProps) {
  const { startCheckout } = useBillingApi();
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
      </CardContent>
    </Card>
  );
}

'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { HugeiconsIcon } from '@hugeicons/react';
import { CheckmarkCircle01Icon, Cancel01Icon } from '@hugeicons/core-free-icons';
import {
  DEFAULT_PLANS,
  displayAmount,
  fetchPublicPlans,
  freeTrialFeatures,
  proFeatures,
  type PublicPlans,
} from '@/lib/plans';

function FeatureList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-2 text-sm">
      {items.map((item) => {
        const missing = item === 'No export';
        return (
          <li key={item} className="flex items-start gap-2">
            <HugeiconsIcon
              icon={missing ? Cancel01Icon : CheckmarkCircle01Icon}
              size={18}
              className={missing ? 'mt-0.5 shrink-0 text-muted-foreground' : 'mt-0.5 shrink-0 text-primary'}
              aria-hidden="true"
            />
            <span className={missing ? 'text-muted-foreground' : 'text-foreground'}>{item}</span>
          </li>
        );
      })}
    </ul>
  );
}

// The two tiers, from GET /billing/plans. It renders the defaults first (they
// match the backend's) and swaps in the live answer when it arrives.
export default function PricingPlans() {
  const [live, setLive] = useState<PublicPlans | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchPublicPlans(controller.signal).then((plans) => {
      if (plans) setLive(plans);
    });
    return () => controller.abort();
  }, []);

  const plans = live?.plans ?? DEFAULT_PLANS.plans;
  const price = live?.pro_price ?? DEFAULT_PLANS.pro_price;

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <section
        aria-labelledby="plan-trial"
        className="flex flex-col gap-6 rounded-xl border border-border bg-card p-6 text-card-foreground"
      >
        <div className="space-y-2">
          <h2 id="plan-trial" className="text-xl font-semibold">
            Free trial
          </h2>
          <p className="text-3xl font-bold">$0</p>
          <p className="text-sm text-muted-foreground">
            Try Auto Author on one chapter of your own book. No card needed.
          </p>
        </div>
        <FeatureList items={freeTrialFeatures(plans.free)} />
        <Link
          href="/auth/sign-up"
          data-goatcounter-click="cta-pricing-trial"
          className="mt-auto rounded-md border border-border px-4 py-2 text-center font-semibold text-foreground hover:bg-accent"
        >
          Start free trial
        </Link>
      </section>

      <section
        aria-labelledby="plan-pro"
        className="flex flex-col gap-6 rounded-xl border-2 border-primary bg-card p-6 text-card-foreground"
      >
        <div className="space-y-2">
          <h2 id="plan-pro" className="text-xl font-semibold">
            Pro
          </h2>
          {price && (
            <p className="text-3xl font-bold">
              {displayAmount(price.amount)}
              <span className="text-base font-normal text-muted-foreground"> / {price.period}</span>
            </p>
          )}
          <p className="text-sm text-muted-foreground">
            Write the whole book: every chapter, and a manuscript you can take anywhere.
          </p>
        </div>
        <FeatureList items={proFeatures(plans.pro)} />
        <Link
          href="/auth/sign-up"
          data-goatcounter-click="cta-pricing-pro"
          className="mt-auto rounded-md bg-primary px-4 py-2 text-center font-semibold text-primary-foreground hover:bg-primary/90"
        >
          Start with the free trial
        </Link>
      </section>
    </div>
  );
}

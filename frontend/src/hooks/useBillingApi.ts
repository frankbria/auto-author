import { useCallback } from 'react';

import { useAuthFetch } from '@/hooks/useAuthFetch';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export type CheckoutSession = {
  url: string;
};

export type PortalSession = {
  url: string;
};

/** A null window is unlimited. */
export type PlanQuotas = Record<'free' | 'pro', { daily: number | null; monthly: number | null }>;

/** The auto-renewal terms to show verbatim before the subscribe action (#770). */
export type RenewalDisclosure = {
  version: string;
  text: string;
  sha256: string;
  price_id: string;
};

/**
 * Hook for billing operations against the better-auth backend.
 * All requests are cookie-authenticated via useAuthFetch (credentials: 'include').
 */
export const useBillingApi = () => {
  const { authFetch } = useAuthFetch({ baseUrl: API_BASE_URL });

  /** Calling this IS the consent: pass the sha256 of the disclosure the user agreed to. */
  const startCheckout = useCallback(
    async (plan: 'pro', disclosureSha256: string): Promise<CheckoutSession> => {
      return authFetch<CheckoutSession>('/billing/checkout', {
        method: 'POST',
        body: JSON.stringify({
          plan,
          accept_renewal_terms: true,
          disclosure_sha256: disclosureSha256,
        }),
      });
    },
    [authFetch]
  );

  const getRenewalDisclosure = useCallback(
    (): Promise<RenewalDisclosure> => authFetch<RenewalDisclosure>('/billing/disclosure'),
    [authFetch]
  );

  const openBillingPortal = useCallback(async (): Promise<PortalSession> => {
    return authFetch<PortalSession>('/billing/portal', {
      method: 'POST',
    });
  }, [authFetch]);

  /** Per-plan AI generation caps, straight from the backend's quota settings (#766). */
  const getPlanQuotas = useCallback(
    (): Promise<PlanQuotas> => authFetch<PlanQuotas>('/billing/quotas'),
    [authFetch]
  );

  return {
    startCheckout,
    openBillingPortal,
    getPlanQuotas,
    getRenewalDisclosure,
  };
};

export default useBillingApi;

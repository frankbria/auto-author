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

/**
 * Hook for billing operations against the better-auth backend.
 * All requests are cookie-authenticated via useAuthFetch (credentials: 'include').
 */
export const useBillingApi = () => {
  const { authFetch } = useAuthFetch({ baseUrl: API_BASE_URL });

  const startCheckout = useCallback(
    async (plan: 'pro' = 'pro'): Promise<CheckoutSession> => {
      return authFetch<CheckoutSession>('/billing/checkout', {
        method: 'POST',
        body: JSON.stringify({ plan }),
      });
    },
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
  };
};

export default useBillingApi;

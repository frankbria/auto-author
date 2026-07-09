import { useCallback } from 'react';

import { useAuthFetch } from '@/hooks/useAuthFetch';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export type CheckoutSession = {
  url: string;
};

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

  return {
    startCheckout,
  };
};

export default useBillingApi;

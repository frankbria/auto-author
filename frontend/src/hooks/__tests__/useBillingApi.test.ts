import { renderHook } from '@testing-library/react';
import useBillingApi from '../useBillingApi';
import { useAuthFetch } from '../useAuthFetch';

jest.mock('../useAuthFetch');

describe('useBillingApi', () => {
  const authFetch = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (useAuthFetch as jest.Mock).mockReturnValue({ authFetch });
  });

  it('startCheckout POSTs the plan with consent to the exact disclosure shown (#770)', async () => {
    authFetch.mockResolvedValue({ url: 'https://checkout.stripe.com/session/abc' });
    const { result } = renderHook(() => useBillingApi());

    const response = await result.current.startCheckout('pro', 'abc123');

    const [path, opts] = authFetch.mock.calls[0];
    expect(path).toBe('/billing/checkout');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual({
      plan: 'pro',
      accept_renewal_terms: true,
      disclosure_sha256: 'abc123',
    });
    expect(response).toEqual({ url: 'https://checkout.stripe.com/session/abc' });
  });

  it('getRenewalDisclosure GETs /billing/disclosure', async () => {
    const disclosure = { version: 'v1', text: 'renews', sha256: 'h', price_id: 'price_1' };
    authFetch.mockResolvedValue(disclosure);
    const { result } = renderHook(() => useBillingApi());

    await expect(result.current.getRenewalDisclosure()).resolves.toEqual(disclosure);
    expect(authFetch).toHaveBeenCalledWith('/billing/disclosure');
  });

  it('propagates errors from the backend', async () => {
    authFetch.mockRejectedValue(new Error('You are already on this plan.'));
    const { result } = renderHook(() => useBillingApi());

    await expect(result.current.startCheckout('pro', 'abc123')).rejects.toThrow(
      'You are already on this plan.'
    );
  });

  it('openBillingPortal POSTs to /billing/portal and returns the url', async () => {
    authFetch.mockResolvedValue({ url: 'https://billing.stripe.com/p/session/abc' });
    const { result } = renderHook(() => useBillingApi());

    const response = await result.current.openBillingPortal();

    expect(authFetch).toHaveBeenCalledWith('/billing/portal', { method: 'POST' });
    expect(response).toEqual({ url: 'https://billing.stripe.com/p/session/abc' });
  });

  it('propagates portal errors from the backend', async () => {
    authFetch.mockRejectedValue(new Error('No billing account yet'));
    const { result } = renderHook(() => useBillingApi());

    await expect(result.current.openBillingPortal()).rejects.toThrow(
      'No billing account yet'
    );
  });
});

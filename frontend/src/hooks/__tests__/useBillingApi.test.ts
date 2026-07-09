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

  it('startCheckout POSTs to /billing/checkout with the plan and returns the url', async () => {
    authFetch.mockResolvedValue({ url: 'https://checkout.stripe.com/session/abc' });
    const { result } = renderHook(() => useBillingApi());

    const response = await result.current.startCheckout('pro');

    expect(authFetch).toHaveBeenCalledWith('/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ plan: 'pro' }),
    });
    expect(response).toEqual({ url: 'https://checkout.stripe.com/session/abc' });
  });

  it('defaults to the pro plan when no argument is given', async () => {
    authFetch.mockResolvedValue({ url: 'https://checkout.stripe.com/session/def' });
    const { result } = renderHook(() => useBillingApi());

    await result.current.startCheckout();

    const [path, opts] = authFetch.mock.calls[0];
    expect(path).toBe('/billing/checkout');
    expect(JSON.parse(opts.body)).toEqual({ plan: 'pro' });
  });

  it('propagates errors from the backend', async () => {
    authFetch.mockRejectedValue(new Error('You are already on this plan.'));
    const { result } = renderHook(() => useBillingApi());

    await expect(result.current.startCheckout('pro')).rejects.toThrow(
      'You are already on this plan.'
    );
  });
});

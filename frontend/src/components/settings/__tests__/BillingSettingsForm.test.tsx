import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import BillingSettingsForm from '../BillingSettingsForm';
import { toast } from '@/lib/toast';

jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));
const mockToast = toast as unknown as jest.Mock;

const mockStartCheckout = jest.fn();
const mockOpenBillingPortal = jest.fn();
jest.mock('@/hooks/useBillingApi', () => ({
  useBillingApi: () => ({
    startCheckout: mockStartCheckout,
    openBillingPortal: mockOpenBillingPortal,
  }),
}));

describe('BillingSettingsForm', () => {
  beforeEach(() => {
    mockToast.mockClear();
    mockStartCheckout.mockReset();
    mockOpenBillingPortal.mockReset();
  });

  it('shows an Upgrade button for a free plan', () => {
    render(<BillingSettingsForm plan="free" />);

    expect(screen.getByText(/free plan/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upgrade to pro/i })).toBeInTheDocument();
  });

  const realLocation = window.location;
  afterEach(() => {
    Object.defineProperty(window, 'location', { value: realLocation, writable: true });
  });

  it('starts checkout and redirects to the returned url on click', async () => {
    const assignSpy = jest.fn();
    Object.defineProperty(window, 'location', {
      value: { assign: assignSpy },
      writable: true,
    });
    mockStartCheckout.mockResolvedValue({ url: 'https://checkout.stripe.com/session/xyz' });

    render(<BillingSettingsForm plan="free" />);
    fireEvent.click(screen.getByRole('button', { name: /upgrade to pro/i }));

    expect(screen.getByRole('button', { name: /redirecting/i })).toBeDisabled();

    await waitFor(() => expect(mockStartCheckout).toHaveBeenCalledWith('pro'));
    await waitFor(() =>
      expect(assignSpy).toHaveBeenCalledWith('https://checkout.stripe.com/session/xyz')
    );
  });

  it('shows a destructive toast and re-enables the button on error', async () => {
    mockStartCheckout.mockRejectedValue(new Error('You are already on this plan.'));

    render(<BillingSettingsForm plan="free" />);
    fireEvent.click(screen.getByRole('button', { name: /upgrade to pro/i }));

    await waitFor(() =>
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          variant: 'destructive',
          description: 'You are already on this plan.',
        })
      )
    );
    expect(screen.getByRole('button', { name: /upgrade to pro/i })).toBeEnabled();
  });

  it('shows a pro-plan state with no Upgrade button', () => {
    render(<BillingSettingsForm plan="pro" />);

    expect(screen.getByText(/pro plan/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /upgrade to pro/i })).not.toBeInTheDocument();
  });

  // --- Billing portal (issue #222) ---
  it('opens the billing portal and redirects for a pro user', async () => {
    const assignSpy = jest.fn();
    Object.defineProperty(window, 'location', {
      value: { assign: assignSpy },
      writable: true,
    });
    mockOpenBillingPortal.mockResolvedValue({
      url: 'https://billing.stripe.com/p/session/xyz',
    });

    render(<BillingSettingsForm plan="pro" hasBillingAccount />);
    fireEvent.click(screen.getByRole('button', { name: /manage billing/i }));

    expect(screen.getByRole('button', { name: /redirecting/i })).toBeDisabled();

    await waitFor(() => expect(mockOpenBillingPortal).toHaveBeenCalled());
    await waitFor(() =>
      expect(assignSpy).toHaveBeenCalledWith('https://billing.stripe.com/p/session/xyz')
    );
  });

  it('shows a destructive toast and re-enables Manage billing on portal error', async () => {
    mockOpenBillingPortal.mockRejectedValue(new Error('Payment provider error'));

    render(<BillingSettingsForm plan="pro" hasBillingAccount />);
    fireEvent.click(screen.getByRole('button', { name: /manage billing/i }));

    await waitFor(() =>
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          variant: 'destructive',
          description: 'Payment provider error',
        })
      )
    );
    expect(screen.getByRole('button', { name: /manage billing/i })).toBeEnabled();
  });

  it('does not show Manage billing for a free user with no billing account', () => {
    render(<BillingSettingsForm plan="free" />);
    expect(screen.queryByRole('button', { name: /manage billing/i })).not.toBeInTheDocument();
  });

  it('shows BOTH Manage billing and Upgrade for a lapsed (restricted) user', () => {
    // A lapsed subscriber must be able to fix their payment method (portal)
    // or start a fresh checkout — the backend allows both deliberately.
    render(<BillingSettingsForm plan="restricted" hasBillingAccount />);

    expect(screen.getByRole('button', { name: /manage billing/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upgrade to pro/i })).toBeInTheDocument();
    // The heading must not mislabel a lapsed subscriber as "Free plan".
    expect(screen.getByText(/subscription is inactive/i)).toBeInTheDocument();
    expect(screen.queryByText(/free plan/i)).not.toBeInTheDocument();
  });
});

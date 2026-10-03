import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import BillingSettingsForm from '../BillingSettingsForm';
import { toast } from '@/lib/toast';

// jsdom 26 (jest 30) defines window.location as non-configurable and gives
// Location no `href` setter, so the old Object.defineProperty(window,'location')
// stub throws "Cannot redefine property: location". Navigation now goes through
// @/lib/navigation, which is mockable. Same assertions, real seam.
jest.mock('@/lib/navigation', () => ({
  navigateTo: jest.fn(),
  reloadPage: jest.fn(),
}));

import { navigateTo } from '@/lib/navigation';
const mockNavigateTo = navigateTo as jest.MockedFunction<typeof navigateTo>;

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
const mockGetPlanQuotas = jest.fn();
const mockGetRenewalDisclosure = jest.fn();
jest.mock('@/hooks/useBillingApi', () => ({
  useBillingApi: () => ({
    startCheckout: mockStartCheckout,
    openBillingPortal: mockOpenBillingPortal,
    getPlanQuotas: mockGetPlanQuotas,
    getRenewalDisclosure: mockGetRenewalDisclosure,
  }),
}));

const DISCLOSURE = {
  version: '2026-10-02',
  text:
    'Auto Author Pro is $12.00 per month, charged to your payment method today and again at the ' +
    'start of each billing period. Your subscription renews automatically until you cancel. ' +
    'Cancel anytime in Auto Author under Settings → Billing → Manage billing.',
  sha256: 'sha-current',
  price_id: 'price_pro',
};

/** Tick the auto-renewal consent box once the disclosure has loaded. */
const agree = async () => fireEvent.click(await screen.findByRole('checkbox', { name: /i agree/i }));

const QUOTAS = {
  free: { daily: 10, monthly: 100 },
  pro: { daily: 50, monthly: 500 },
};

describe('BillingSettingsForm', () => {
  beforeEach(() => {
    mockToast.mockClear();
    mockStartCheckout.mockReset();
    mockOpenBillingPortal.mockReset();
    mockGetPlanQuotas.mockReset();
    mockGetPlanQuotas.mockResolvedValue(QUOTAS);
    mockGetRenewalDisclosure.mockReset();
    mockGetRenewalDisclosure.mockResolvedValue(DISCLOSURE);
  });

  // --- Auto-renewal disclosure + consent (issue #770, CA ARL / ROSCA) ---
  it('shows price, interval, auto-renewal and the cancel path next to the Upgrade button', async () => {
    render(<BillingSettingsForm plan="free" />);

    const disclosure = await screen.findByText(/\$12\.00 per month/);
    expect(disclosure).toHaveTextContent(/renews automatically until you cancel/i);
    expect(disclosure).toHaveTextContent(/settings → billing → manage billing/i);
    // Next to the subscribe action: same container as the button, and the
    // checkbox is described by the disclosure for screen readers.
    const button = screen.getByRole('button', { name: /upgrade to pro/i });
    expect(button.parentElement).toContainElement(disclosure);
    expect(screen.getByRole('checkbox', { name: /i agree/i })).toHaveAccessibleDescription(
      DISCLOSURE.text
    );
  });

  it('keeps Upgrade disabled until the consent box is ticked (unchecked by default)', async () => {
    render(<BillingSettingsForm plan="free" />);

    const box = await screen.findByRole('checkbox', { name: /i agree/i });
    expect(box).not.toBeChecked();
    expect(screen.getByRole('button', { name: /upgrade to pro/i })).toBeDisabled();

    fireEvent.click(box);
    expect(screen.getByRole('button', { name: /upgrade to pro/i })).toBeEnabled();
  });

  it('links the consent label to the Terms of Service', async () => {
    render(<BillingSettingsForm plan="free" />);
    expect(await screen.findByRole('link', { name: /terms of service/i })).toHaveAttribute(
      'href',
      '/terms'
    );
  });

  it('pauses upgrading when the renewal terms cannot be loaded', async () => {
    mockGetRenewalDisclosure.mockRejectedValue(new Error('Payment provider error'));
    render(<BillingSettingsForm plan="free" />);

    expect(await screen.findByText(/subscription terms are unavailable/i)).toBeInTheDocument();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upgrade to pro/i })).toBeDisabled();
  });

  it('reloads changed terms and clears the agreement when checkout reports them stale', async () => {
    mockStartCheckout.mockRejectedValue(new Error('The subscription terms have changed'));
    render(<BillingSettingsForm plan="free" />);
    await agree();

    const changed = { ...DISCLOSURE, text: 'Auto Author Pro is $15.00 per month.', sha256: 'sha-new' };
    mockGetRenewalDisclosure.mockResolvedValue(changed);
    fireEvent.click(screen.getByRole('button', { name: /upgrade to pro/i }));

    expect(await screen.findByText(/\$15\.00 per month/)).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: /i agree/i })).not.toBeChecked();
    expect(screen.getByRole('button', { name: /upgrade to pro/i })).toBeDisabled();
  });

  it('does not load renewal terms for a Pro user', async () => {
    render(<BillingSettingsForm plan="pro" />);
    await waitFor(() => expect(mockGetPlanQuotas).toHaveBeenCalled());
    expect(mockGetRenewalDisclosure).not.toHaveBeenCalled();
  });

  it('names the concrete Free vs Pro AI limits, read from the API', async () => {
    render(<BillingSettingsForm plan="free" />);

    expect(
      await screen.findByText(/free: 10 AI generations per day \(100 per month\)/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/pro: 50 per day \(500 per month\)/i)).toBeInTheDocument();
    expect(screen.queryByText(/full access to every/i)).not.toBeInTheDocument();
  });

  it('says "unlimited" for a disabled (null) window instead of 0', async () => {
    mockGetPlanQuotas.mockResolvedValue({
      free: { daily: null, monthly: 100 },
      pro: { daily: null, monthly: null },
    });
    render(<BillingSettingsForm plan="free" />);

    expect(
      await screen.findByText(
        /free: unlimited AI generations per day \(100 per month\)\. pro: unlimited per day \(unlimited per month\)/i
      )
    ).toBeInTheDocument();
  });

  it('tells a Pro user their own cap', async () => {
    render(<BillingSettingsForm plan="pro" />);

    expect(
      await screen.findByText(/50 AI generations per day \(500 per month\)/i)
    ).toBeInTheDocument();
  });

  it('still renders the plan and upgrade button if the limits cannot be loaded', async () => {
    mockGetPlanQuotas.mockRejectedValue(new Error('boom'));
    render(<BillingSettingsForm plan="free" />);

    expect(screen.getByRole('button', { name: /upgrade to pro/i })).toBeInTheDocument();
    await waitFor(() => expect(mockGetPlanQuotas).toHaveBeenCalled());
  });

  it('shows an Upgrade button for a free plan', () => {
    render(<BillingSettingsForm plan="free" />);

    expect(screen.getByText(/free plan/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upgrade to pro/i })).toBeInTheDocument();
  });


  it('starts checkout and redirects to the returned url on click', async () => {
    mockNavigateTo.mockClear();
    mockStartCheckout.mockResolvedValue({ url: 'https://checkout.stripe.com/session/xyz' });

    render(<BillingSettingsForm plan="free" />);
    await agree();
    fireEvent.click(screen.getByRole('button', { name: /upgrade to pro/i }));

    expect(screen.getByRole('button', { name: /redirecting/i })).toBeDisabled();

    await waitFor(() => expect(mockStartCheckout).toHaveBeenCalledWith('pro', 'sha-current'));
    await waitFor(() =>
      expect(mockNavigateTo).toHaveBeenCalledWith('https://checkout.stripe.com/session/xyz')
    );
  });

  it('shows a destructive toast and re-enables the button on error', async () => {
    mockStartCheckout.mockRejectedValue(new Error('You are already on this plan.'));

    render(<BillingSettingsForm plan="free" />);
    await agree();
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
    mockNavigateTo.mockClear();
    mockOpenBillingPortal.mockResolvedValue({
      url: 'https://billing.stripe.com/p/session/xyz',
    });

    render(<BillingSettingsForm plan="pro" hasBillingAccount />);
    fireEvent.click(screen.getByRole('button', { name: /manage billing/i }));

    expect(screen.getByRole('button', { name: /redirecting/i })).toBeDisabled();

    await waitFor(() => expect(mockOpenBillingPortal).toHaveBeenCalled());
    await waitFor(() =>
      expect(mockNavigateTo).toHaveBeenCalledWith('https://billing.stripe.com/p/session/xyz')
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

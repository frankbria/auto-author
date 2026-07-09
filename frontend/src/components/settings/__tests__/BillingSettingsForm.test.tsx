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
jest.mock('@/hooks/useBillingApi', () => ({
  useBillingApi: () => ({ startCheckout: mockStartCheckout }),
}));

describe('BillingSettingsForm', () => {
  beforeEach(() => {
    mockToast.mockClear();
    mockStartCheckout.mockReset();
  });

  it('shows an Upgrade button for a free plan', () => {
    render(<BillingSettingsForm plan="free" />);

    expect(screen.getByText(/free plan/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upgrade to pro/i })).toBeInTheDocument();
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
});

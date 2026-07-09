import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from '@/app/dashboard/settings/page';
import { toast } from '@/lib/toast';

jest.mock('@/lib/auth-client', () => ({
  useSession: jest.fn(() => ({
    data: { user: { email: 'a@b.com', name: 'Ann' }, session: { token: 'tok' } },
  })),
  authClient: {
    changePassword: jest.fn().mockResolvedValue({ data: {}, error: null }),
    listSessions: jest.fn().mockResolvedValue({ data: [], error: null }),
    revokeSession: jest.fn().mockResolvedValue({ data: {}, error: null }),
    revokeOtherSessions: jest.fn().mockResolvedValue({ data: {}, error: null }),
    twoFactor: {
      enable: jest.fn().mockResolvedValue({ data: null, error: null }),
      disable: jest.fn().mockResolvedValue({ data: {}, error: null }),
      verifyTotp: jest.fn().mockResolvedValue({ data: {}, error: null }),
    },
  },
}));

jest.mock('next-themes', () => ({
  useTheme: () => ({
    setTheme: jest.fn(),
    theme: 'dark',
  }),
}));

jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));
const mockToast = toast as unknown as jest.Mock;

const mockAuthFetch = jest.fn();
jest.mock('@/hooks/useAuthFetch', () => ({
  useAuthFetch: () => ({ authFetch: mockAuthFetch }),
}));

const loadedProfile = (
  plan: string,
  preferences: Record<string, unknown> = {},
  stripe_customer_id: string | null = null
) => ({
  id: 'u1',
  auth_id: 'auth-1',
  email: 'a@b.com',
  plan,
  stripe_customer_id,
  preferences,
});

const setSearch = (search: string) => {
  window.history.pushState({}, '', `${window.location.pathname}${search}`);
};

describe('SettingsPage billing tab', () => {
  beforeEach(() => {
    mockToast.mockClear();
    mockAuthFetch.mockReset();
    setSearch('');
  });

  it('shows the current plan from GET /users/me on the Billing tab', async () => {
    const user = userEvent.setup();
    mockAuthFetch.mockResolvedValue(loadedProfile('pro'));
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save settings/i })).toBeEnabled()
    );
    await user.click(screen.getByRole('tab', { name: /billing/i }));

    expect(screen.getByText(/pro plan/i)).toBeInTheDocument();
  });

  it('hides the shared Save button on the Billing tab', async () => {
    const user = userEvent.setup();
    mockAuthFetch.mockResolvedValue(loadedProfile('free'));
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save settings/i })).toBeEnabled()
    );
    await user.click(screen.getByRole('tab', { name: /billing/i }));

    expect(screen.queryByRole('button', { name: /save settings/i })).not.toBeInTheDocument();
  });

  it('selects the Billing tab and shows a success toast for ?checkout=success', async () => {
    setSearch('?checkout=success');
    mockAuthFetch.mockResolvedValue(loadedProfile('free'));
    render(<SettingsPage />);

    await waitFor(() =>
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Checkout complete' })
      )
    );
    expect(screen.getByRole('tab', { name: /billing/i })).toHaveAttribute(
      'data-state',
      'active'
    );
    expect(window.location.search).toBe('');
  });

  it('shows Manage billing for a lapsed user with a Stripe customer (issue #222)', async () => {
    const user = userEvent.setup();
    mockAuthFetch.mockResolvedValue(loadedProfile('restricted', {}, 'cus_lapsed_001'));
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save settings/i })).toBeEnabled()
    );
    await user.click(screen.getByRole('tab', { name: /billing/i }));

    expect(screen.getByRole('button', { name: /manage billing/i })).toBeInTheDocument();
  });

  // --- ?tab= deep-link (issue #222) ---
  it('selects the Billing tab for ?tab=billing without any toast', async () => {
    setSearch('?tab=billing');
    mockAuthFetch.mockResolvedValue(loadedProfile('free'));
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByRole('tab', { name: /billing/i })).toHaveAttribute(
        'data-state',
        'active'
      )
    );
    expect(mockToast).not.toHaveBeenCalled();
  });

  it('ignores an unknown ?tab= value and stays on the default tab', async () => {
    setSearch('?tab=bogus');
    mockAuthFetch.mockResolvedValue(loadedProfile('free'));
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByRole('tab', { name: /writing/i })).toHaveAttribute(
        'data-state',
        'active'
      )
    );
  });

  it('selects the Billing tab and shows a canceled toast for ?checkout=cancel', async () => {
    setSearch('?checkout=cancel');
    mockAuthFetch.mockResolvedValue(loadedProfile('free'));
    render(<SettingsPage />);

    await waitFor(() =>
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Checkout canceled' })
      )
    );
    expect(screen.getByRole('tab', { name: /billing/i })).toHaveAttribute(
      'data-state',
      'active'
    );
    expect(window.location.search).toBe('');
  });
});

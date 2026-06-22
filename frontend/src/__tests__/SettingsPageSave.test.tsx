import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SettingsPage from '@/app/dashboard/settings/page';

// Mock auth session
jest.mock('@/lib/auth-client', () => ({
  useSession: jest.fn(() => ({
    data: { user: { email: 'a@b.com', name: 'Ann' } },
  })),
}));

// Capture toast calls
const mockToast = jest.fn();
jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({ toast: mockToast }),
}));

// Mock the authenticated fetch hook
const mockAuthFetch = jest.fn();
jest.mock('@/hooks/useAuthFetch', () => ({
  useAuthFetch: () => ({ authFetch: mockAuthFetch }),
}));

describe('SettingsPage save', () => {
  beforeEach(() => {
    mockToast.mockClear();
    mockAuthFetch.mockReset();
  });

  const patchCall = () =>
    mockAuthFetch.mock.calls.find(([, opts]) => opts?.method === 'PATCH');

  it('initializes toggles from persisted preferences (GET /users/me)', async () => {
    mockAuthFetch.mockResolvedValue({
      preferences: { theme: 'dark', email_notifications: false },
    });
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByLabelText('Dark Mode')).toBeChecked()
    );
    expect(screen.getByLabelText('Email Notifications')).not.toBeChecked();
  });

  it('preserves loaded preferences (e.g. marketing_emails) and maps toggles on save', async () => {
    mockAuthFetch.mockResolvedValue({
      preferences: { theme: 'light', email_notifications: true, marketing_emails: true },
    });
    render(<SettingsPage />);

    // Save is gated until the initial load completes.
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save settings/i })).toBeEnabled()
    );

    // Toggle dark mode on so theme maps to 'dark'
    fireEvent.click(screen.getByLabelText('Dark Mode'));
    fireEvent.click(screen.getByRole('button', { name: /save settings/i }));

    await waitFor(() => expect(patchCall()).toBeDefined());
    const [path, options] = patchCall()!;
    expect(path).toBe('/users/me');
    // marketing_emails must survive even though the UI never exposes it.
    expect(JSON.parse(options.body)).toEqual({
      preferences: { theme: 'dark', email_notifications: true, marketing_emails: true },
    });
    await waitFor(() =>
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Settings saved' })
      )
    );
  });

  it('disables Save until preferences finish loading', () => {
    // Never resolves -> stays in loading state.
    mockAuthFetch.mockReturnValue(new Promise(() => {}));
    render(<SettingsPage />);
    expect(screen.getByRole('button', { name: /loading/i })).toBeDisabled();
  });

  it('shows a destructive toast when the save fails', async () => {
    // Load succeeds, the PATCH fails.
    mockAuthFetch.mockResolvedValueOnce({ preferences: {} });
    mockAuthFetch.mockRejectedValueOnce(new Error('boom'));
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save settings/i })).toBeEnabled()
    );
    fireEvent.click(screen.getByRole('button', { name: /save settings/i }));

    await waitFor(() =>
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Save failed', variant: 'destructive' })
      )
    );
  });

  it('keeps Save disabled (and offers retry) when the preference load fails', async () => {
    mockAuthFetch.mockRejectedValueOnce(new Error('load failed'));
    render(<SettingsPage />);

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /save settings/i })).toBeDisabled();
    // No PATCH is possible while preferences are unknown.
    expect(patchCall()).toBeUndefined();

    // Retry succeeds -> Save becomes enabled.
    mockAuthFetch.mockResolvedValueOnce({ preferences: { marketing_emails: true } });
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save settings/i })).toBeEnabled()
    );
  });
});

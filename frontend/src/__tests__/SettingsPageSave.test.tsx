import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from '@/app/dashboard/settings/page';
import { toast } from '@/lib/toast';
import { invalidateUserPreferencesCache } from '@/hooks/useUserPreferences';

// Mock auth session
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

// Theme changes must be applied immediately via next-themes.
// A FRESH setTheme identity is returned on every render (as next-themes can
// do after a theme change) — the page must not let that re-fire its loader.
const mockSetTheme = jest.fn();
jest.mock('next-themes', () => ({
  useTheme: () => ({
    setTheme: (...args: unknown[]) => mockSetTheme(...args),
    theme: 'dark',
  }),
}));

// Capture toast calls. The component calls the base toast({ title, variant })
// imported from '@/lib/toast', so mock that module with a callable toast.
jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));
const mockToast = toast as unknown as jest.Mock;

// Mock the authenticated fetch hook (useProfileApi sits on top of it)
const mockAuthFetch = jest.fn();
jest.mock('@/hooks/useAuthFetch', () => ({
  useAuthFetch: () => ({ authFetch: mockAuthFetch }),
}));

const loadedProfile = (preferences: Record<string, unknown>) => ({
  id: 'u1',
  auth_id: 'auth-1',
  email: 'a@b.com',
  preferences,
});

describe('SettingsPage', () => {
  beforeEach(() => {
    mockToast.mockClear();
    mockSetTheme.mockClear();
    (invalidateUserPreferencesCache as jest.Mock).mockClear();
    mockAuthFetch.mockReset();
  });

  const patchCall = () =>
    mockAuthFetch.mock.calls.find(([, opts]) => opts?.method === 'PATCH');

  it('initializes writing controls from persisted preferences (GET /users/me)', async () => {
    mockAuthFetch.mockResolvedValue(
      loadedProfile({
        theme: 'light',
        email_notifications: false,
        default_writing_style: 'academic',
        auto_save_interval: 10,
      })
    );
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByLabelText('Default Writing Style')).toHaveValue('academic')
    );
    expect(screen.getByLabelText('Auto-save Interval (seconds)')).toHaveValue(10);
    expect(screen.getByLabelText('Editor Theme')).toHaveValue('light');
  });

  it('preserves unexposed preference fields and maps edits on save', async () => {
    mockAuthFetch.mockResolvedValue(
      loadedProfile({
        theme: 'light',
        email_notifications: true,
        marketing_emails: true,
        future_flag: true, // not rendered anywhere — must survive a save
      })
    );
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save settings/i })).toBeEnabled()
    );

    fireEvent.change(screen.getByLabelText('Default Writing Style'), {
      target: { value: 'technical' },
    });
    fireEvent.click(screen.getByRole('button', { name: /save settings/i }));

    await waitFor(() => expect(patchCall()).toBeDefined());
    const [path, options] = patchCall()!;
    expect(path).toBe('/users/me');
    const body = JSON.parse(options.body);
    expect(body.preferences).toMatchObject({
      theme: 'light',
      email_notifications: true,
      marketing_emails: true,
      future_flag: true,
      default_writing_style: 'technical',
    });
    await waitFor(() =>
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Settings saved' })
      )
    );
    // Consumers of the shared preference cache see fresh values
    expect(invalidateUserPreferencesCache).toHaveBeenCalled();
  });

  it('keeps in-progress edits when the theme changes (loader must not re-fire)', async () => {
    mockAuthFetch.mockResolvedValue(
      loadedProfile({ theme: 'dark', default_writing_style: 'conversational' })
    );
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save settings/i })).toBeEnabled()
    );
    const getCallsAfterLoad = mockAuthFetch.mock.calls.length;

    fireEvent.change(screen.getByLabelText('Default Writing Style'), {
      target: { value: 'technical' },
    });
    // Changing the theme hands the page a new setTheme identity — this used
    // to re-run loadPreferences and clobber the style edit back to stored.
    fireEvent.change(screen.getByLabelText('Editor Theme'), {
      target: { value: 'light' },
    });

    expect(screen.getByLabelText('Default Writing Style')).toHaveValue('technical');
    expect(mockAuthFetch.mock.calls.length).toBe(getCallsAfterLoad);
  });

  it('applies theme changes immediately via next-themes', async () => {
    mockAuthFetch.mockResolvedValue(loadedProfile({ theme: 'dark' }));
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByLabelText('Editor Theme')).toHaveValue('dark')
    );
    fireEvent.change(screen.getByLabelText('Editor Theme'), {
      target: { value: 'light' },
    });

    expect(mockSetTheme).toHaveBeenCalledWith('light');
    // Applied immediately — persisted only on save
    expect(patchCall()).toBeUndefined();
  });

  it('disables Save and shows an error for an out-of-range auto-save interval', async () => {
    mockAuthFetch.mockResolvedValue(loadedProfile({ auto_save_interval: 5 }));
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save settings/i })).toBeEnabled()
    );
    fireEvent.change(screen.getByLabelText('Auto-save Interval (seconds)'), {
      target: { value: '45' },
    });

    expect(screen.getByRole('alert')).toHaveTextContent(/between 3 and 30/i);
    expect(screen.getByRole('button', { name: /save settings/i })).toBeDisabled();
  });

  it('shows export defaults on the Export tab and saves them', async () => {
    const user = userEvent.setup();
    mockAuthFetch.mockResolvedValue(
      loadedProfile({ default_export_format: 'epub', include_empty_chapters: true })
    );
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save settings/i })).toBeEnabled()
    );
    await user.click(screen.getByRole('tab', { name: /export/i }));

    expect(screen.getByRole('radio', { name: 'EPUB' })).toBeChecked();
    expect(screen.getByLabelText('Include Empty Chapters')).toBeChecked();
    // Page size options only apply to PDF
    expect(screen.queryByRole('radio', { name: 'Letter' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('radio', { name: 'PDF' }));
    expect(screen.getByRole('radio', { name: 'A4' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('radio', { name: 'A4' }));
    fireEvent.click(screen.getByRole('button', { name: /save settings/i }));

    await waitFor(() => expect(patchCall()).toBeDefined());
    const body = JSON.parse(patchCall()![1].body);
    expect(body.preferences).toMatchObject({
      default_export_format: 'pdf',
      default_page_size: 'A4',
      include_empty_chapters: true,
    });
  });

  it('shows all five notification toggles on the Notifications tab', async () => {
    const user = userEvent.setup();
    mockAuthFetch.mockResolvedValue(
      loadedProfile({ email_notifications: false, writing_reminders: true })
    );
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save settings/i })).toBeEnabled()
    );
    await user.click(screen.getByRole('tab', { name: /notifications/i }));

    expect(screen.getByLabelText('Email Notifications')).not.toBeChecked();
    expect(screen.getByLabelText('Marketing Emails')).not.toBeChecked();
    expect(screen.getByLabelText('Writing Reminders')).toBeChecked();
    expect(screen.getByLabelText('Progress Updates')).toBeChecked();
    expect(screen.getByLabelText('Backup Notifications')).toBeChecked();
  });

  it('renders security sections without the shared Save button', async () => {
    const user = userEvent.setup();
    mockAuthFetch.mockResolvedValue(loadedProfile({}));
    render(<SettingsPage />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save settings/i })).toBeEnabled()
    );
    await user.click(screen.getByRole('tab', { name: /security/i }));

    expect(screen.getByLabelText('Current Password')).toBeInTheDocument();
    expect(screen.getByText('Two-Factor Authentication')).toBeInTheDocument();
    expect(screen.getByText('Active Sessions')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /save settings/i })).not.toBeInTheDocument();
  });

  it('disables Save until preferences finish loading', () => {
    // Never resolves -> stays in loading state.
    mockAuthFetch.mockReturnValue(new Promise(() => {}));
    render(<SettingsPage />);
    expect(screen.getByRole('button', { name: /loading/i })).toBeDisabled();
  });

  it('shows a destructive toast when the save fails', async () => {
    // Load succeeds, the PATCH fails.
    mockAuthFetch.mockResolvedValueOnce(loadedProfile({}));
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
    mockAuthFetch.mockResolvedValueOnce(loadedProfile({ marketing_emails: true }));
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save settings/i })).toBeEnabled()
    );
  });
});

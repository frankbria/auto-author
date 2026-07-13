import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import UserProfile from '@/app/profile/page';
import { invalidateUserPreferencesCache } from '@/hooks/useUserPreferences';
import { useSession } from '@/lib/auth-client';

// Merge-contract tests for the Profile page (issue #204): a save must send the
// FULL preferences object, not a 3-field reconstruction that wipes the
// Settings-page fields. Unlike ProfilePage.test.tsx (which mocks
// react-hook-form and useProfileApi wholesale), this suite runs the real form
// and real useProfileApi on top of a mocked authFetch — mirroring
// SettingsPageSave.test.tsx.

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));

const mockAuthFetch = jest.fn();
jest.mock('@/hooks/useAuthFetch', () => ({
  useAuthFetch: () => ({ authFetch: mockAuthFetch }),
}));

const fullPreferences = {
  theme: 'light',
  email_notifications: true,
  marketing_emails: false,
  // Settings-page fields the Profile page does not render — must survive a save.
  default_writing_style: 'academic',
  auto_save_interval: 10,
  default_export_format: 'epub',
  include_empty_chapters: true,
  writing_reminders: true,
  future_flag: true,
};

const profile = (preferences: Record<string, unknown>) => ({
  id: 'u1',
  auth_id: 'auth-1',
  email: 'a@b.com',
  first_name: 'Ann',
  last_name: 'Author',
  display_name: 'Ann Author',
  bio: 'hi',
  preferences,
});

const patchCall = () =>
  mockAuthFetch.mock.calls.find(([, opts]) => opts?.method === 'PATCH');

describe('ProfilePage save preserves preferences (#204)', () => {
  beforeEach(() => {
    mockAuthFetch.mockReset();
    (invalidateUserPreferencesCache as jest.Mock).mockClear();
  });

  it('sends the full merged preferences object on save, preserving unexposed fields', async () => {
    mockAuthFetch.mockImplementation(async (_path: string, opts?: { method?: string }) => {
      if (opts?.method === 'PATCH') {
        return profile({ ...fullPreferences, theme: 'dark' });
      }
      return profile(fullPreferences);
    });

    render(<UserProfile />);

    await waitFor(() => expect(screen.getByLabelText('Theme')).toHaveValue('light'));
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save changes/i })).toBeEnabled()
    );

    fireEvent.change(screen.getByLabelText('Theme'), { target: { value: 'dark' } });
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => expect(patchCall()).toBeDefined());
    const [path, options] = patchCall()!;
    expect(path).toBe('/users/me');
    const body = JSON.parse(options.body);
    expect(body.preferences).toMatchObject({
      ...fullPreferences,
      theme: 'dark',
    });
  });

  it('invalidates the shared preferences cache after a successful save', async () => {
    mockAuthFetch.mockResolvedValue(profile(fullPreferences));

    render(<UserProfile />);
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save changes/i })).toBeEnabled()
    );

    fireEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => expect(patchCall()).toBeDefined());
    await waitFor(() => expect(invalidateUserPreferencesCache).toHaveBeenCalled());
  });

  it('disables save while preferences are loading and after a failed load', async () => {
    let rejectLoad: (err: Error) => void;
    mockAuthFetch.mockImplementation(
      () => new Promise((_, reject) => (rejectLoad = reject))
    );

    render(<UserProfile />);

    // Still loading (button reads "Loading…") — a save now would wipe the
    // preferences subdocument.
    expect(screen.getByRole('button', { name: /loading/i })).toBeDisabled();

    await act(async () => {
      rejectLoad!(new Error('network down'));
    });

    // Failed load — saving stays disabled so we can't overwrite stored preferences.
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save changes/i })).toBeDisabled()
    );
    expect(screen.getByRole('alert')).toHaveTextContent(/couldn.t load your current preferences/i);
    expect(patchCall()).toBeUndefined();
  });

  it('still captures server preferences when the user edits before hydration resolves', async () => {
    let resolveLoad: (p: unknown) => void;
    mockAuthFetch.mockImplementation(async (_path: string, opts?: { method?: string }) => {
      if (opts?.method === 'PATCH') return profile(fullPreferences);
      return new Promise((resolve) => (resolveLoad = resolve));
    });

    render(<UserProfile />);

    // User starts typing before the profile fetch resolves. Hydration must
    // keep the edit (keepDirtyValues) while still filling untouched fields
    // and capturing the full preferences object.
    fireEvent.change(screen.getByLabelText('First name'), { target: { value: 'Zed' } });

    await act(async () => {
      resolveLoad!(profile(fullPreferences));
    });

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save changes/i })).toBeEnabled()
    );
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => expect(patchCall()).toBeDefined());
    const body = JSON.parse(patchCall()![1].body);
    // Unexposed Settings fields survive even on the dirty path.
    expect(body.preferences).toMatchObject({
      default_writing_style: 'academic',
      auto_save_interval: 10,
      future_flag: true,
    });
    // The user's in-flight edit survives hydration…
    expect(body.first_name).toBe('Zed');
    // …and untouched backend-only fields still hydrate, so the save can't
    // overwrite them with session-seeded defaults (e.g. bio: '').
    expect(body.bio).toBe('hi');
    expect(body.display_name).toBe('Ann Author');
  });

  it('re-arms the save guard when the signed-in user changes', async () => {
    mockAuthFetch.mockResolvedValue(profile(fullPreferences));
    const { rerender } = render(<UserProfile />);
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /save changes/i })).toBeEnabled()
    );

    // Session switches to a different account; its profile load never
    // resolves. The previous user's retained preferences must not be
    // saveable into the new account during that window.
    mockAuthFetch.mockImplementation(() => new Promise(() => {}));
    (useSession as jest.Mock).mockReturnValue({
      data: {
        user: { id: 'user-2', email: 'b@c.com', name: 'Bob Other', image: null },
        session: { token: 'tok2', id: 'sess-2' },
      },
    });
    rerender(<UserProfile />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /loading/i })).toBeDisabled()
    );
  });
});

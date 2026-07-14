import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import UserProfile from '@/app/profile/page';
import { useSession } from '@/lib/auth-client';

// Type-to-confirm tests for account deletion (issue #216): the Delete-account
// button must stay disabled until the user types the account email, matching
// the DeleteBookModal safeguard. Like ProfilePageSave.test.tsx, this suite
// runs the real form, real Radix Dialog, and real useProfileApi over a mocked
// authFetch — the legacy ProfilePage.test.tsx mocks those wholesale and cannot
// express disabled/enabled semantics.

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
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

// The global better-auth mock's session user — the confirmation phrase.
const SESSION_EMAIL = 'test@example.com';

const profile = () => ({
  id: 'u1',
  auth_id: 'auth-1',
  email: 'profile@example.com',
  first_name: 'Ann',
  last_name: 'Author',
  display_name: 'Ann Author',
  bio: 'hi',
  preferences: { theme: 'light', email_notifications: true, marketing_emails: false },
});

const deleteCall = () =>
  mockAuthFetch.mock.calls.find(([, opts]) => opts?.method === 'DELETE');

const openDeleteDialog = async () => {
  render(<UserProfile />);
  await waitFor(() =>
    expect(screen.getByRole('button', { name: /save changes/i })).toBeEnabled()
  );
  fireEvent.click(screen.getByRole('button', { name: /^delete account$/i }));
  return {
    input: await screen.findByLabelText(/to confirm/i),
    confirmButton: screen.getByRole('button', { name: /delete account permanently/i }),
  };
};

describe('ProfilePage account deletion type-to-confirm (#216)', () => {
  beforeEach(() => {
    mockAuthFetch.mockReset();
    mockPush.mockClear();
    mockAuthFetch.mockResolvedValue(profile());
    // Re-seed the session explicitly: a per-test mockReturnValue override
    // (the fallback test below) must not leak into other tests via ordering.
    (useSession as jest.Mock).mockReturnValue({
      data: {
        user: { id: 'test-user-id', email: SESSION_EMAIL, name: 'Test User', image: null },
        session: { token: 't', id: 's' },
      },
      isPending: false,
    });
  });

  it('disables the confirm button until the exact account email is typed', async () => {
    const { input, confirmButton } = await openDeleteDialog();

    // Empty input → disabled.
    expect(confirmButton).toBeDisabled();

    // Wrong text → still disabled, mismatch hint shown, nothing deleted.
    fireEvent.change(input, { target: { value: 'wrong@example.com' } });
    expect(confirmButton).toBeDisabled();
    expect(screen.getByRole('alert')).toHaveTextContent(/must match/i);
    fireEvent.click(confirmButton);
    expect(deleteCall()).toBeUndefined();

    // Case-sensitive exact match required (consistent with DeleteBookModal).
    fireEvent.change(input, { target: { value: SESSION_EMAIL.toUpperCase() } });
    expect(confirmButton).toBeDisabled();
  });

  it('enables on exact match; confirming sends DELETE /users/me and redirects home', async () => {
    const { input, confirmButton } = await openDeleteDialog();

    fireEvent.change(input, { target: { value: SESSION_EMAIL } });
    expect(confirmButton).toBeEnabled();

    fireEvent.click(confirmButton);

    await waitFor(() => expect(deleteCall()).toBeDefined());
    expect(deleteCall()![0]).toBe('/users/me');
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/'));
  });

  it('submits on Enter when the confirmation matches', async () => {
    const { input } = await openDeleteDialog();

    fireEvent.change(input, { target: { value: SESSION_EMAIL } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => expect(deleteCall()).toBeDefined());
  });

  it('resets the confirmation when the dialog is cancelled and reopened', async () => {
    const { input, confirmButton } = await openDeleteDialog();

    fireEvent.change(input, { target: { value: SESSION_EMAIL } });
    expect(confirmButton).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }));
    fireEvent.click(screen.getByRole('button', { name: /^delete account$/i }));

    const reopenedInput = await screen.findByLabelText(/to confirm/i);
    expect(reopenedInput).toHaveValue('');
    expect(
      screen.getByRole('button', { name: /delete account permanently/i })
    ).toBeDisabled();
    expect(deleteCall()).toBeUndefined();
  });

  it('falls back to the hydrated profile email when the session has none', async () => {
    // Route-mocked E2E (and any session without an email) must still be able
    // to confirm — the phrase falls back to the profile fetched from the API.
    (useSession as jest.Mock).mockReturnValue({
      data: {
        user: { id: 'test-user-id', name: 'Test User', image: null },
        session: { token: 't', id: 's' },
      },
      isPending: false,
    });

    const { input, confirmButton } = await openDeleteDialog();

    expect(confirmButton).toBeDisabled();
    fireEvent.change(input, { target: { value: 'profile@example.com' } });
    expect(confirmButton).toBeEnabled();
  });
});

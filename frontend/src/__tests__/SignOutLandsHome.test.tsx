/**
 * Signing out of a protected page lands on `/` (#886).
 *
 * The session store drops the session as soon as signOut is called, and
 * ProtectedRoute reacts to that before the caller's `router.push('/')` runs,
 * so the user used to land on `/auth/sign-in?redirect=<the page they left>`.
 */
import React, { useSyncExternalStore } from 'react';
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useRouter, usePathname } from 'next/navigation';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { signOutOrNotify } from '@/lib/sign-out';

let session: { user: { id: string } } | null;
const listeners = new Set<() => void>();
const setSession = (next: typeof session) => {
  session = next;
  listeners.forEach((l) => l());
};
const mockSignOut = jest.fn();

jest.mock('next/navigation', () => ({ useRouter: jest.fn(), usePathname: jest.fn() }));
jest.mock('@/lib/toast', () => ({ toast: jest.fn() }));
jest.mock('@/lib/auth-client', () => ({
  useSession: () => ({
    data: useSyncExternalStore(
      (l) => (listeners.add(l), () => listeners.delete(l)),
      () => session
    ),
    isPending: false,
  }),
  authClient: { signOut: () => mockSignOut() },
}));

const router = { push: jest.fn() };

// What user-button.tsx does.
function SignOutButton() {
  return (
    <button onClick={async () => { if (await signOutOrNotify()) router.push('/'); }}>
      Sign out
    </button>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  delete process.env.NEXT_PUBLIC_BYPASS_AUTH;
  (useRouter as jest.Mock).mockReturnValue(router);
  (usePathname as jest.Mock).mockReturnValue('/dashboard/books/b1');
  setSession({ user: { id: 'u1' } });
  // The real client clears the session before its promise resolves.
  mockSignOut.mockImplementation(async () => {
    setSession(null);
    return { error: null };
  });
});

function renderPage() {
  render(
    <ProtectedRoute>
      <SignOutButton />
    </ProtectedRoute>
  );
}

it('signing out lands on the home page, not on sign-in with a way back', async () => {
  renderPage();
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));

  await waitFor(() => expect(router.push).toHaveBeenCalledWith('/'));
  expect(router.push).toHaveBeenCalledTimes(1);
});

it('a session that ends without a sign-out still goes to sign-in with a way back', async () => {
  renderPage();
  act(() => setSession(null));

  await waitFor(() =>
    expect(router.push).toHaveBeenCalledWith('/auth/sign-in?redirect=%2Fdashboard%2Fbooks%2Fb1')
  );
});

it('after a sign-out, a later session that ends is redirected as usual', async () => {
  renderPage();
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
  await waitFor(() => expect(router.push).toHaveBeenCalledWith('/'));

  // Signed in again in the same tab, then the session expires.
  act(() => setSession({ user: { id: 'u1' } }));
  router.push.mockClear();
  act(() => setSession(null));

  await waitFor(() =>
    expect(router.push).toHaveBeenCalledWith('/auth/sign-in?redirect=%2Fdashboard%2Fbooks%2Fb1')
  );
});

it('a sign-out that fails leaves the guard as it was', async () => {
  mockSignOut.mockResolvedValue({ error: { message: 'offline' } });
  renderPage();
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
  await waitFor(() => expect(mockSignOut).toHaveBeenCalled());

  act(() => setSession(null));

  await waitFor(() =>
    expect(router.push).toHaveBeenCalledWith('/auth/sign-in?redirect=%2Fdashboard%2Fbooks%2Fb1')
  );
});

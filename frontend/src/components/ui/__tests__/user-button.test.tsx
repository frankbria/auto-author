import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter } from 'next/navigation';

import { UserButton } from '@/components/ui/user-button';
import { authClient, useSession } from '@/lib/auth-client';
import { toast } from '@/lib/toast';

jest.mock('next/navigation', () => ({ useRouter: jest.fn() }));
jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));

const mockSignOut = authClient.signOut as jest.Mock;
const mockToast = toast as unknown as jest.Mock;

/**
 * #796 — a failed sign-out was ignored: the menu navigated home as if it had
 * worked, with the session still alive.
 */
describe('UserButton sign out', () => {
  const push = jest.fn();

  const signOut = async () => {
    const user = userEvent.setup();
    render(<UserButton />);
    await user.click(screen.getByRole('button', { name: 'Account menu' }));
    await user.click(await screen.findByRole('menuitem', { name: /sign out/i }));
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue({ push });
    (useSession as jest.Mock).mockReturnValue({
      data: { user: { id: 'u1', name: 'Ann Author', email: 'ann@example.com' }, session: { token: 't' } },
    });
  });

  it('goes home after signing out', async () => {
    mockSignOut.mockResolvedValue({ data: { success: true }, error: null });

    await signOut();

    await waitFor(() => expect(push).toHaveBeenCalledWith('/'));
    expect(mockToast).not.toHaveBeenCalled();
  });

  it.each([
    ['the server refuses', () => Promise.resolve({ data: null, error: { message: 'nope' } })],
    ['the request never arrives', () => Promise.reject(new Error('Failed to fetch'))],
  ])('says so and stays put when %s', async (_case, outcome) => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
    mockSignOut.mockImplementation(outcome);

    await signOut();

    await waitFor(() =>
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Could not sign out', variant: 'destructive' })
      )
    );
    expect(push).not.toHaveBeenCalled();
  });
});

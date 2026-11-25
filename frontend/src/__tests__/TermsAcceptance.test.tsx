/**
 * An account whose recorded Terms version is older than TERMS_VERSION, or
 * missing, is asked to accept before the protected page loads (#961).
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { useRouter, usePathname } from 'next/navigation';
import { acceptTerms, useSession } from '@/lib/auth-client';
import { signOutOrNotify } from '@/lib/sign-out';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { TERMS_VERSION } from '@/lib/constants/legal';

expect.extend(toHaveNoViolations);

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  usePathname: jest.fn(),
}));

jest.mock('@/lib/auth-client', () => ({
  useSession: jest.fn(),
  acceptTerms: jest.fn(),
}));

jest.mock('@/lib/sign-out', () => ({
  signOutOrNotify: jest.fn(),
  signOutUnderway: () => false,
  endSignOut: jest.fn(),
}));

const push = jest.fn();
const refetch = jest.fn();

function signedInWith(termsVersion?: unknown) {
  (useSession as jest.Mock).mockReturnValue({
    data: {
      user: { id: 'u1', email: 'a@example.com', name: 'A', termsVersion },
      session: { id: 's1' },
    },
    isPending: false,
    error: null,
    refetch,
  });
}

function renderPage() {
  return render(
    <ProtectedRoute>
      <div>Protected Content</div>
    </ProtectedRoute>
  );
}

const acceptButton = () => screen.getByRole('button', { name: /i accept the terms of service/i });

beforeEach(() => {
  jest.clearAllMocks();
  delete process.env.NEXT_PUBLIC_BYPASS_AUTH;
  (useRouter as jest.Mock).mockReturnValue({ push });
  (usePathname as jest.Mock).mockReturnValue('/dashboard');
});

describe('Terms re-acceptance gate (#961)', () => {
  it('shows the page to an account that accepted the current version', () => {
    signedInWith(TERMS_VERSION);
    renderPage();
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /i accept/i })).not.toBeInTheDocument();
  });

  it.each([
    ['an older version', '2000-01-01'],
    ['no version (created before #789)', undefined],
  ])('asks an account with %s to accept instead of showing the page', (_label, version) => {
    signedInWith(version);
    renderPage();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 1, name: /accept the terms of service/i })
    ).toBeInTheDocument();
    expect(acceptButton()).toBeEnabled();
    const link = screen.getByRole('link', { name: /read the terms of service/i });
    expect(link).toHaveAttribute('href', '/terms');
    expect(link).toHaveAccessibleName(/opens in a new tab/i);
  });

  it('records the acceptance server-side and then reloads the session', async () => {
    signedInWith('2000-01-01');
    (acceptTerms as jest.Mock).mockResolvedValue({ data: { termsVersion: TERMS_VERSION }, error: null });
    renderPage();

    await userEvent.click(acceptButton());

    expect(acceptTerms).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(refetch).toHaveBeenCalledTimes(1));
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  // The acceptance is recorded; a session reload that fails must not ask again.
  it('shows the page once accepted even if the session reload fails', async () => {
    signedInWith('2000-01-01');
    refetch.mockRejectedValueOnce(new Error('503'));
    (acceptTerms as jest.Mock).mockResolvedValue({ data: { termsVersion: TERMS_VERSION }, error: null });
    renderPage();

    await userEvent.click(acceptButton());

    expect(await screen.findByText('Protected Content')).toBeInTheDocument();
  });

  it('asks for a reload when the Terms changed while the screen was open', async () => {
    signedInWith('2000-01-01');
    (acceptTerms as jest.Mock).mockResolvedValue({ data: null, error: { status: 409 } });
    renderPage();

    await userEvent.click(acceptButton());

    expect(await screen.findByRole('alert')).toHaveTextContent(/changed while this page was open\. reload/i);
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('keeps its alert region in the accessibility tree before any failure', () => {
    signedInWith(undefined);
    renderPage();
    const region = screen.getByRole('alert');
    expect(region).toBeEmptyDOMElement();
    expect(region.className).not.toMatch(/\b(hidden|empty:hidden)\b/);
  });

  it('says so when the server refuses, and lets the user try again', async () => {
    signedInWith(undefined);
    (acceptTerms as jest.Mock).mockResolvedValue({ data: null, error: { status: 500 } });
    renderPage();

    await userEvent.click(acceptButton());

    expect(await screen.findByRole('alert')).toHaveTextContent(/could not record your acceptance/i);
    expect(refetch).not.toHaveBeenCalled();
    expect(acceptButton()).toBeEnabled();
  });

  it('says so when the request never arrives', async () => {
    signedInWith(undefined);
    (acceptTerms as jest.Mock).mockRejectedValue(new TypeError('Failed to fetch'));
    renderPage();

    await userEvent.click(acceptButton());

    expect(await screen.findByRole('alert')).toHaveTextContent(/could not record your acceptance/i);
    expect(refetch).not.toHaveBeenCalled();
  });

  it('marks the button busy while the acceptance is being recorded', async () => {
    signedInWith(undefined);
    let finish: (v: unknown) => void = () => {};
    (acceptTerms as jest.Mock).mockReturnValue(new Promise((r) => (finish = r)));
    renderPage();

    await userEvent.click(acceptButton());

    const busy = screen.getByRole('button', { name: /accepting/i });
    expect(busy).toBeDisabled();
    expect(busy).toHaveAttribute('aria-busy', 'true');
    finish({ data: {}, error: null });
    await waitFor(() => expect(refetch).toHaveBeenCalled());
  });

  it('lets a user who does not accept sign out to the home page', async () => {
    signedInWith(undefined);
    (signOutOrNotify as jest.Mock).mockResolvedValue(true);
    renderPage();

    await userEvent.click(screen.getByRole('button', { name: /sign out/i }));

    await waitFor(() => expect(push).toHaveBeenCalledWith('/'));
    expect(acceptTerms).not.toHaveBeenCalled();
  });

  it('stays put when the sign-out fails', async () => {
    signedInWith(undefined);
    (signOutOrNotify as jest.Mock).mockResolvedValue(false);
    renderPage();

    await userEvent.click(screen.getByRole('button', { name: /sign out/i }));

    await waitFor(() => expect(signOutOrNotify).toHaveBeenCalled());
    expect(push).not.toHaveBeenCalled();
  });

  // Terms section 7 promises cancelling online; declining must not take that,
  // the data download or account deletion away.
  it.each(['/dashboard/settings', '/profile'])(
    'still opens %s, where the account can be cancelled, downloaded or deleted',
    (path) => {
      (usePathname as jest.Mock).mockReturnValue(path);
      signedInWith(undefined);
      renderPage();
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    }
  );

  it('asks on every other page, including ones that only start like an exit', () => {
    (usePathname as jest.Mock).mockReturnValue('/dashboard/settingsX');
    signedInWith(undefined);
    renderPage();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('links a user who does not accept to billing, and to their data and account', () => {
    signedInWith(undefined);
    renderPage();
    expect(screen.getByRole('link', { name: /cancel your subscription/i })).toHaveAttribute(
      'href',
      '/dashboard/settings?tab=billing'
    );
    expect(
      screen.getByRole('link', { name: /download your data or delete your account/i })
    ).toHaveAttribute('href', '/profile');
  });

  it('returns focus to the accept button when recording fails', async () => {
    signedInWith(undefined);
    (acceptTerms as jest.Mock).mockResolvedValue({ data: null, error: { status: 500 } });
    renderPage();

    await userEvent.click(acceptButton());

    await screen.findByText(/could not record your acceptance/i);
    expect(acceptButton()).toHaveFocus();
  });

  it('is the page landmark the skip link targets, and has no axe violations', async () => {
    signedInWith(undefined);
    const { container } = renderPage();
    expect(container.querySelector('main#main-content')).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });
});

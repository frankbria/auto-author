import { render, screen, within } from '@testing-library/react';
import HomePage from '@/app/page';
import { useSession } from '@/lib/auth-client';

// The landing page is public and carries the positioning adopted on
// 2026-10-28. These tests pin the adopted copy, the ways in, and the claims
// the positioning doc says the page must never make.

jest.mock('@/lib/auth-client', () => ({
  useSession: jest.fn().mockReturnValue({ data: null, isPending: false, error: null }),
  authClient: { signOut: jest.fn() },
}));

// An async server component; the analytics tag has its own tests.
jest.mock('@/components/marketing/Analytics', () => ({
  __esModule: true,
  default: () => null,
}));

const signedIn = {
  data: { user: { id: 'u1', email: 'a@example.com', name: 'A' }, session: { id: 's1' } },
  isPending: false,
  error: null,
};

describe('Landing page', () => {
  beforeEach(() => {
    (useSession as jest.Mock).mockReturnValue({ data: null, isPending: false, error: null });
  });

  test('leads with the adopted headline', () => {
    render(<HomePage />);
    const h1 = screen.getByRole('heading', { level: 1 });
    expect(h1).toHaveTextContent(
      'Your book is already in your head. Auto Author asks the questions that get it out.'
    );
  });

  test('carries the three proof points and the steps of how it works', () => {
    render(<HomePage />);
    expect(screen.getByText('Questions for every chapter, not one prompt for the whole book.')).toBeInTheDocument();
    expect(screen.getByText('Answer by typing or by speaking.')).toBeInTheDocument();
    expect(screen.getByText(/A real editor, and your manuscript exports as DOCX, EPUB, PDF or Markdown/)).toBeInTheDocument();
    const how = screen.getByRole('heading', { name: 'How it works' }).parentElement as HTMLElement;
    expect(within(how).getAllByRole('listitem')).toHaveLength(7);
  });

  test('offers the free trial and the pricing page to a signed-out visitor', () => {
    render(<HomePage />);
    const trial = screen.getByRole('link', { name: 'Try Auto Author on one chapter, free' });
    expect(trial).toHaveAttribute('href', '/auth/sign-up');
    expect(screen.getByRole('link', { name: 'See pricing' })).toHaveAttribute('href', '/pricing');
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/auth/sign-in');
    expect(screen.queryByRole('link', { name: 'Go to dashboard' })).not.toBeInTheDocument();
  });

  test('gives a signed-in visitor the dashboard and sign-out instead of sign-up', () => {
    (useSession as jest.Mock).mockReturnValue(signedIn);
    render(<HomePage />);
    const header = screen.getByRole('banner');
    expect(within(header).getByRole('link', { name: 'Go to dashboard' })).toHaveAttribute('href', '/dashboard');
    expect(within(header).getByRole('button', { name: 'Sign out' })).toBeInTheDocument();
    expect(within(header).queryByRole('link', { name: 'Start free trial' })).not.toBeInTheDocument();
  });

  test('shows the page while the session is still loading, not a spinner', () => {
    (useSession as jest.Mock).mockReturnValue({ data: null, isPending: true, error: null });
    render(<HomePage />);
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    expect(document.querySelector('.animate-spin')).toBeNull();
  });

  test('makes none of the claims the positioning rules out', () => {
    const { container } = render(<HomePage />);
    const text = (container.textContent ?? '').toLowerCase();
    for (const banned of [
      'in your voice',
      'voice interviewer',
      'calls you',
      'kdp',
      'isbn',
      'cover design',
      'publish',
      'human editor',
      'free plan',
      'write your book free',
      'in an hour',
      'minutes',
      'clients will',
      'roi',
      'testimonial',
    ]) {
      expect(text).not.toContain(banned);
    }
  });
});

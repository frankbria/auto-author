import { render, screen, waitFor, within } from '@testing-library/react';
import PricingPage from '@/app/pricing/page';

jest.mock('@/lib/auth-client', () => ({
  useSession: jest.fn().mockReturnValue({ data: null, isPending: false, error: null }),
  authClient: { signOut: jest.fn() },
}));

jest.mock('@/components/marketing/Analytics', () => ({
  __esModule: true,
  default: () => null,
}));

const card = (name: string) =>
  screen.getByRole('heading', { level: 2, name }).closest('section') as HTMLElement;

function respondWith(body: unknown, ok = true) {
  (global.fetch as jest.Mock).mockResolvedValue({ ok, json: async () => body });
}

describe('Pricing page', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  test('shows the adopted plans before the live answer arrives', async () => {
    (global.fetch as jest.Mock).mockReturnValue(new Promise(() => {}));
    render(<PricingPage />);

    const trial = card('Free trial');
    expect(within(trial).getByText('$0')).toBeInTheDocument();
    expect(within(trial).getByText("30 AI generations in total, which don't reset")).toBeInTheDocument();
    expect(within(trial).getByText("One chapter's interview questions and AI draft")).toBeInTheDocument();
    expect(within(trial).getByText('No export')).toBeInTheDocument();

    const pro = card('Pro');
    expect(pro).toHaveTextContent('$49 / month');
    expect(within(pro).getByText('50 AI generations a day (500 a month)')).toBeInTheDocument();
    expect(within(pro).getByText('Export to PDF, DOCX, EPUB and Markdown')).toBeInTheDocument();
    expect(within(pro).getByText('Cancel anytime')).toBeInTheDocument();
  });

  test('asks the public plans endpoint without credentials', async () => {
    respondWith(null, false);
    render(<PricingPage />);
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    const [url, init] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toMatch(/\/billing\/plans$/);
    expect(init).toMatchObject({ credentials: 'omit' });
  });

  test('takes the price and limits from the live answer', async () => {
    respondWith({
      pro_price: { amount: '$59.00', period: '3 months' },
      plans: {
        free: { daily: null, monthly: null, total: 40, draft_chapters: 2, export: false },
        pro: { daily: 60, monthly: 600, total: null, draft_chapters: null, export: true },
      },
    });
    render(<PricingPage />);
    await waitFor(() => expect(card('Pro')).toHaveTextContent('$59 / 3 months'));
    expect(within(card('Pro')).getByText('60 AI generations a day (600 a month)')).toBeInTheDocument();
    expect(within(card('Free trial')).getByText("40 AI generations in total, which don't reset")).toBeInTheDocument();
    expect(within(card('Free trial')).getByText('Interview questions and AI drafts for 2 chapters')).toBeInTheDocument();
  });

  test('keeps the adopted price when the live answer has none', async () => {
    respondWith({
      pro_price: null,
      plans: {
        free: { daily: null, monthly: null, total: 30, draft_chapters: 1, export: false },
        pro: { daily: 50, monthly: 500, total: null, draft_chapters: null, export: true },
      },
    });
    render(<PricingPage />);
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(card('Pro')).toHaveTextContent('$49 / month');
  });

  test('keeps the adopted plans when the endpoint fails', async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error('offline'));
    render(<PricingPage />);
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(card('Pro')).toHaveTextContent('$49 / month');
  });

  test('sends both plans to sign-up and calls the free tier a trial, never a plan', () => {
    (global.fetch as jest.Mock).mockReturnValue(new Promise(() => {}));
    const { container } = render(<PricingPage />);
    for (const name of ['Start free trial', 'Start with the free trial']) {
      for (const link of screen.getAllByRole('link', { name })) {
        expect(link).toHaveAttribute('href', '/auth/sign-up');
      }
    }
    const text = (container.textContent ?? '').toLowerCase();
    expect(text).not.toContain('free plan');
    expect(text).not.toMatch(/year(ly)?\b|annual/);
    expect(text).not.toContain('refund');
  });
});

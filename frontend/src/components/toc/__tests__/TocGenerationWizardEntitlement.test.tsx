/**
 * TocGenerationWizard tests (issue #247 + step-flow coverage).
 *
 * Entitlement routing: a restricted user's analyze-summary 402 used to be
 * silently swallowed by the nested catch in checkTocReadiness, and any other
 * 402 was flattened to a message string rendered with a useless "Try Again"
 * panel. These tests pin the new behavior: entitlement denials reach the
 * ERROR step with an Upgrade affordance deep-linking to
 * /dashboard/settings?tab=billing.
 *
 * Step components are stubbed so the wizard's own state machine (readiness →
 * questions → generating → review → accept/regenerate) is what's under test.
 * ErrorDisplay is real — its upgrade-vs-retry branch is the affordance under
 * test. next/navigation and @/lib/auth-client are mocked in jest.setup.ts.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { useRouter } from 'next/navigation';
import TocGenerationWizard from '../TocGenerationWizard';
import { bookClient } from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient');

// The wizard's mount effect depends on trackOperation's identity — the mock
// must return a stable object or the wizard re-fires the effect forever.
jest.mock('@/hooks/usePerformanceTracking', () => {
  const stable = {
    trackOperation: async (_name: string, fn: () => Promise<unknown>) => ({
      data: await fn(),
    }),
  };
  return { usePerformanceTracking: () => stable };
});

jest.mock('../ReadinessChecker', () => ({
  __esModule: true,
  default: () => {
    const React = require('react');
    return React.createElement('div', { 'data-testid': 'readiness-checker' });
  },
}));

jest.mock('../NotReadyMessage', () => ({
  __esModule: true,
  default: () => {
    const React = require('react');
    return React.createElement('div', { 'data-testid': 'not-ready' });
  },
}));

jest.mock('../TocGenerating', () => ({
  __esModule: true,
  default: () => {
    const React = require('react');
    return React.createElement('div', { 'data-testid': 'toc-generating' });
  },
}));

jest.mock('../ClarifyingQuestions', () => ({
  __esModule: true,
  default: ({ onSubmit }: { onSubmit: (r: unknown[]) => void }) => {
    const React = require('react');
    return React.createElement(
      'button',
      { onClick: () => onSubmit([{ question: 'Q1', answer: 'A1' }]) },
      'submit-answers'
    );
  },
}));

jest.mock('../TocReview', () => ({
  __esModule: true,
  default: ({ onAccept, onRegenerate }: { onAccept: () => void; onRegenerate: () => void }) => {
    const React = require('react');
    return React.createElement(
      'div',
      null,
      React.createElement('button', { onClick: onAccept }, 'accept-toc'),
      React.createElement('button', { onClick: onRegenerate }, 'regenerate-toc')
    );
  },
}));

const mockedBookClient = bookClient as jest.Mocked<typeof bookClient>;

function errorWithStatus(message: string, statusCode: number) {
  const err = new Error(message) as Error & { statusCode: number };
  err.statusCode = statusCode;
  return err;
}

const ENTITLEMENT_MESSAGE = 'Your current plan does not include AI features.';

const READY_READINESS = {
  is_ready_for_toc: true,
  confidence_score: 0.9,
  analysis: 'Looks good.',
  suggestions: [],
  word_count: 800,
  character_count: 4800,
  meets_minimum_requirements: true,
} as never;

const NOT_READY_READINESS = {
  is_ready_for_toc: false,
  confidence_score: 0.2,
  analysis: 'Summary too thin.',
  suggestions: ['Add more detail'],
  word_count: 20,
  character_count: 120,
  meets_minimum_requirements: false,
} as never;

const TOC_RESULT = {
  toc: {
    chapters: [
      { title: 'Chapter 1', subchapters: [{ title: 'Sub 1' }] },
      { title: 'Chapter 2' },
    ],
  },
} as never;

/** Drive the wizard to the REVIEW step (questions answered, TOC generated). */
async function renderToReview() {
  mockedBookClient.analyzeSummary.mockResolvedValue({} as never);
  mockedBookClient.checkTocReadiness.mockResolvedValue(READY_READINESS);
  mockedBookClient.generateQuestions.mockResolvedValue({ questions: ['Q1'] } as never);
  mockedBookClient.generateToc.mockResolvedValue(TOC_RESULT);

  const user = userEvent.setup();
  render(<TocGenerationWizard bookId="book-1" />);

  await user.click(await screen.findByRole('button', { name: 'submit-answers' }));
  await screen.findByRole('button', { name: 'accept-toc' });
  return user;
}

describe('TocGenerationWizard entitlement routing (issue #247)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('routes an analyze-summary 402 to the ERROR step with an Upgrade link (not swallowed, no Try Again)', async () => {
    mockedBookClient.analyzeSummary.mockRejectedValue(
      errorWithStatus(ENTITLEMENT_MESSAGE, 402)
    );

    render(<TocGenerationWizard bookId="book-1" />);

    const upgradeLink = await screen.findByRole('link', { name: /upgrade/i });
    expect(upgradeLink).toHaveAttribute('href', '/dashboard/settings?tab=billing');

    // The entitlement message is shown; the retry affordance is not.
    expect(screen.getByText(ENTITLEMENT_MESSAGE)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();

    // The wizard must not have continued past the paywall.
    expect(mockedBookClient.checkTocReadiness).not.toHaveBeenCalled();

    // No raw payload fragments anywhere.
    expect(screen.queryByText(/"detail"/)).not.toBeInTheDocument();
    expect(screen.queryByText(/402/)).not.toBeInTheDocument();
  });

  it('routes a readiness-check 402 (outer catch) to the entitlement panel', async () => {
    mockedBookClient.analyzeSummary.mockResolvedValue({} as never);
    mockedBookClient.checkTocReadiness.mockRejectedValue(
      errorWithStatus(ENTITLEMENT_MESSAGE, 402)
    );

    render(<TocGenerationWizard bookId="book-1" />);

    const upgradeLink = await screen.findByRole('link', { name: /upgrade/i });
    expect(upgradeLink).toHaveAttribute('href', '/dashboard/settings?tab=billing');
    expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
  });

  it('routes a question-generation 402 to the entitlement panel', async () => {
    mockedBookClient.analyzeSummary.mockResolvedValue({} as never);
    mockedBookClient.checkTocReadiness.mockResolvedValue(READY_READINESS);
    mockedBookClient.generateQuestions.mockRejectedValue(
      errorWithStatus(ENTITLEMENT_MESSAGE, 402)
    );

    render(<TocGenerationWizard bookId="book-1" />);

    expect(await screen.findByRole('link', { name: /upgrade/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
  });

  it('routes a TOC-generation 402 (question submit) to the entitlement panel', async () => {
    mockedBookClient.analyzeSummary.mockResolvedValue({} as never);
    mockedBookClient.checkTocReadiness.mockResolvedValue(READY_READINESS);
    mockedBookClient.generateQuestions.mockResolvedValue({ questions: ['Q1'] } as never);
    mockedBookClient.generateToc.mockRejectedValue(
      errorWithStatus(ENTITLEMENT_MESSAGE, 402)
    );

    const user = userEvent.setup();
    render(<TocGenerationWizard bookId="book-1" />);

    await user.click(await screen.findByRole('button', { name: 'submit-answers' }));

    expect(await screen.findByRole('link', { name: /upgrade/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
  });

  it('still swallows a non-402 analyze-summary failure and proceeds to the readiness check (regression)', async () => {
    mockedBookClient.analyzeSummary.mockRejectedValue(new Error('AI temporarily down'));
    mockedBookClient.checkTocReadiness.mockResolvedValue(NOT_READY_READINESS);

    render(<TocGenerationWizard bookId="book-1" />);

    // Analysis failure is non-fatal: the wizard falls through to the basic
    // readiness check and shows the not-ready step.
    await waitFor(() => {
      expect(mockedBookClient.checkTocReadiness).toHaveBeenCalled();
    });
    expect(await screen.findByTestId('not-ready')).toBeInTheDocument();
  });

  it('keeps the generic Try Again panel for non-entitlement errors, and retry re-runs the readiness check', async () => {
    mockedBookClient.analyzeSummary.mockResolvedValue({} as never);
    mockedBookClient.checkTocReadiness.mockRejectedValueOnce(
      errorWithStatus('Service unavailable', 503)
    );
    mockedBookClient.checkTocReadiness.mockResolvedValue(NOT_READY_READINESS);

    const user = userEvent.setup();
    render(<TocGenerationWizard bookId="book-1" />);

    const retryButton = await screen.findByRole('button', { name: /try again/i });
    expect(screen.queryByRole('link', { name: /upgrade/i })).not.toBeInTheDocument();

    await user.click(retryButton);
    expect(await screen.findByTestId('not-ready')).toBeInTheDocument();
    expect(mockedBookClient.checkTocReadiness).toHaveBeenCalledTimes(2);
  });
});

describe('TocGenerationWizard step flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('walks readiness → questions → generating → review and normalizes chapter fields', async () => {
    await renderToReview();

    expect(mockedBookClient.generateToc).toHaveBeenCalledWith('book-1', [
      { question: 'Q1', answer: 'A1' },
    ]);
  });

  it('accepting the TOC saves it and navigates to the edit-toc page', async () => {
    const push = jest.fn();
    (useRouter as jest.Mock).mockReturnValue({ push });
    mockedBookClient.updateToc.mockResolvedValue({} as never);

    const user = await renderToReview();
    await user.click(screen.getByRole('button', { name: 'accept-toc' }));

    await waitFor(() => {
      expect(mockedBookClient.updateToc).toHaveBeenCalledWith(
        'book-1',
        expect.objectContaining({ chapters: expect.any(Array) })
      );
    });
    expect(push).toHaveBeenCalledWith('/dashboard/books/book-1/edit-toc');
  });

  it('a failed TOC save keeps the review step (no navigation)', async () => {
    const push = jest.fn();
    (useRouter as jest.Mock).mockReturnValue({ push });
    mockedBookClient.updateToc.mockRejectedValue(new Error('save failed'));

    const user = await renderToReview();
    await user.click(screen.getByRole('button', { name: 'accept-toc' }));

    await waitFor(() => {
      expect(mockedBookClient.updateToc).toHaveBeenCalled();
    });
    expect(push).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'accept-toc' })).toBeInTheDocument();
  });

  it('regenerating the TOC calls generateToc again and returns to review', async () => {
    const user = await renderToReview();

    await user.click(screen.getByRole('button', { name: 'regenerate-toc' }));

    await waitFor(() => {
      expect(mockedBookClient.generateToc).toHaveBeenCalledTimes(2);
    });
    expect(await screen.findByRole('button', { name: 'accept-toc' })).toBeInTheDocument();
  });

  it('a regeneration 402 lands on the entitlement panel', async () => {
    const user = await renderToReview();

    mockedBookClient.generateToc.mockRejectedValue(
      errorWithStatus(ENTITLEMENT_MESSAGE, 402)
    );
    await user.click(screen.getByRole('button', { name: 'regenerate-toc' }));

    expect(await screen.findByRole('link', { name: /upgrade/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
  });
});

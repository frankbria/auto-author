import { render, screen } from '@testing-library/react';
import NotReadyMessage from '../NotReadyMessage';
import { SUMMARY_MIN_WORDS, SUMMARY_MIN_CHARACTERS } from '@/lib/constants/summary-readiness';

// Copy pins for issue #218: the NOT_READY screen must not advertise a threshold
// the gate does not enforce. The real gate is 30 words AND 150 characters
// (books.py:1150, ai_service.py:483) — "500-1000 words" was fiction that made a
// passing summary look like a failing one.

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock('@/lib/api/bookClient', () => ({
  bookClient: { analyzeSummary: jest.fn() },
}));

const readiness = {
  is_ready_for_toc: false,
  confidence_score: 0.4,
  analysis: 'Needs more detail.',
  suggestions: ['Add key themes'],
  word_count: 12,
  character_count: 80,
  meets_minimum_requirements: false,
};

const renderMessage = () =>
  render(<NotReadyMessage readiness={readiness} onRetry={jest.fn()} bookId="book-1" />);

describe('NotReadyMessage — threshold copy (#218)', () => {
  it('does not claim a 500-1000 word minimum', () => {
    renderMessage();
    expect(screen.queryByText(/500-1000 words/i)).not.toBeInTheDocument();
  });

  it('states the real minimum the gate enforces', () => {
    renderMessage();
    const tip = screen.getByText(
      new RegExp(`${SUMMARY_MIN_WORDS} words.*${SUMMARY_MIN_CHARACTERS} characters`, 'i')
    );
    expect(tip).toBeInTheDocument();
  });
});

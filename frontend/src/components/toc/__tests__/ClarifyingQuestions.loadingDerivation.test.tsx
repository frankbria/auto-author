import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import ClarifyingQuestions from '../ClarifyingQuestions';
import { bookClient } from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient');
const mockedBookClient = bookClient as jest.Mocked<typeof bookClient>;

/**
 * "Nothing to load" is derived, not written into the fetch's state (#584).
 *
 * The effect used to end with `else { setIsLoadingResponses(false) }` — a
 * synchronous setState in an effect body, announcing a fact that was already
 * knowable from `bookId` and `questions` during render. The state now means one
 * thing, *the fetch has not finished*, and the skeleton reads both conditions
 * where it is rendered.
 *
 * The existing suite passes either way, which is why these are here: they pin
 * the observable behaviour that the else branch was providing, so removing it is
 * a refactor rather than a regression, and reintroducing it is not needed.
 */
describe('ClarifyingQuestions loading skeleton (#584)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const props = {
    questions: ['What is the main theme?'],
    onSubmit: jest.fn(),
    isLoading: false,
    bookId: 'book-1',
  };

  it('shows no skeleton when there are no questions to load responses for', async () => {
    // The case the removed `else` handled. With no questions the fetch never
    // starts, so the state stays at its initial `true` — and nothing may show a
    // loading skeleton on the strength of it.
    render(<ClarifyingQuestions {...props} questions={[]} />);

    // The component keeps an always-mounted polite live region (#349), so the
    // skeleton is addressed by its own test id rather than by role.
    expect(screen.queryByTestId('clarifying-questions-skeleton')).not.toBeInTheDocument();
    expect(mockedBookClient.getQuestionResponses).not.toHaveBeenCalled();
  });

  it('shows no skeleton without a bookId, for the same reason', () => {
    render(<ClarifyingQuestions {...props} bookId="" />);

    expect(screen.queryByTestId('clarifying-questions-skeleton')).not.toBeInTheDocument();
  });

  it('shows the skeleton while a real fetch is in flight, and clears it after', async () => {
    // The counterweight: the derivation must not swallow the state it derives
    // from. A `showLoading` hard-wired to `false` would pass the two tests above
    // and fail this one.
    type Responses = Awaited<ReturnType<typeof bookClient.getQuestionResponses>>;
    let resolveFetch: (value: Responses) => void = () => {};
    mockedBookClient.getQuestionResponses.mockReturnValue(
      new Promise<Responses>((resolve) => {
        resolveFetch = resolve;
      })
    );

    render(<ClarifyingQuestions {...props} />);

    expect(screen.getByTestId('clarifying-questions-skeleton')).toHaveAttribute(
      'aria-busy',
      'true'
    );

    resolveFetch({ responses: [], status: 'ok' });
    await waitFor(() =>
      expect(screen.queryByTestId('clarifying-questions-skeleton')).not.toBeInTheDocument()
    );
  });
});

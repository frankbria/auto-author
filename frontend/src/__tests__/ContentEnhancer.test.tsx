import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ContentEnhancer } from '@/components/chapters/ContentEnhancer';
import { bookClient } from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  bookClient: {
    enhanceChapterText: jest.fn(),
  },
  default: { enhanceChapterText: jest.fn() },
}));

jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));

const mockEnhance = bookClient.enhanceChapterText as jest.Mock;

function setup(content = '<p>The cat sat on the mat.</p>') {
  const onApply = jest.fn();
  render(
    <ContentEnhancer
      bookId="b1"
      chapterId="c1"
      getCurrentContent={() => content}
      onApply={onApply}
    />
  );
  return { onApply };
}

beforeEach(() => jest.clearAllMocks());

it('renders the enhance button', () => {
  setup();
  expect(screen.getByRole('button', { name: /^enhance$/i })).toBeInTheDocument();
});

it('enhances, previews before/after, and applies to the editor', async () => {
  const user = userEvent.setup();
  mockEnhance.mockResolvedValueOnce({
    success: true,
    enhanced: '<p>The cat sat upon the mat.</p>',
    metadata: { enhancement_label: 'Grammar' },
  });
  const { onApply } = setup();

  await user.click(screen.getByRole('button', { name: /^enhance$/i }));
  // The dialog footer also has an "Enhance" submit button; click the last one.
  const enhanceButtons = screen.getAllByRole('button', { name: /^enhance$/i });
  await user.click(enhanceButtons[enhanceButtons.length - 1]);

  await waitFor(() => {
    expect(screen.getByText(/The cat sat on the mat/i)).toBeInTheDocument();
    expect(screen.getByText(/cat sat upon the mat/i)).toBeInTheDocument();
  });

  expect(mockEnhance).toHaveBeenCalledWith('b1', 'c1', {
    content: '<p>The cat sat on the mat.</p>',
    enhancement_type: 'clarity',
  });

  await user.click(screen.getByRole('button', { name: /apply to chapter/i }));
  expect(onApply).toHaveBeenCalledWith('<p>The cat sat upon the mat.</p>');
});

it('blocks enhancing empty content without calling the API', async () => {
  const user = userEvent.setup();
  setup('<p></p>');

  await user.click(screen.getByRole('button', { name: /^enhance$/i }));
  const enhanceButtons = screen.getAllByRole('button', { name: /^enhance$/i });
  await user.click(enhanceButtons[enhanceButtons.length - 1]);

  expect(await screen.findByText(/add some content/i)).toBeInTheDocument();
  expect(mockEnhance).not.toHaveBeenCalled();
});

it('shows an error and returns to options when enhancement fails', async () => {
  const user = userEvent.setup();
  mockEnhance.mockRejectedValueOnce(new Error('AI service unavailable'));
  setup();

  await user.click(screen.getByRole('button', { name: /^enhance$/i }));
  const enhanceButtons = screen.getAllByRole('button', { name: /^enhance$/i });
  await user.click(enhanceButtons[enhanceButtons.length - 1]);

  expect(await screen.findByText(/AI service unavailable/i)).toBeInTheDocument();
  // Still on the options step: the footer submit Enhance button is visible again
  // (the toolbar trigger is aria-hidden while the dialog is open).
  expect(screen.getByRole('button', { name: /^enhance$/i })).toBeInTheDocument();
});

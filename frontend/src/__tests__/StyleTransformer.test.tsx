import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StyleTransformer } from '@/components/chapters/StyleTransformer';
import { bookClient } from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  bookClient: {
    transformChapterStyle: jest.fn(),
  },
  default: { transformChapterStyle: jest.fn() },
}));

jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));

const mockTransform = bookClient.transformChapterStyle as jest.Mock;

function setup(content = '<p>The cat sat on the mat.</p>') {
  const onApply = jest.fn();
  render(
    <StyleTransformer
      bookId="b1"
      chapterId="c1"
      getCurrentContent={() => content}
      onApply={onApply}
    />
  );
  return { onApply };
}

beforeEach(() => jest.clearAllMocks());

it('renders the transform button', () => {
  setup();
  expect(screen.getByRole('button', { name: /transform style/i })).toBeInTheDocument();
});

it('transforms, previews before/after, and applies to the editor', async () => {
  const user = userEvent.setup();
  mockTransform.mockResolvedValueOnce({
    success: true,
    transformed: '<p>The feline reposed upon the rug.</p>',
    metadata: { style_label: 'Academic' },
  });
  const { onApply } = setup();

  await user.click(screen.getByRole('button', { name: /transform style/i }));
  await user.click(screen.getByRole('button', { name: /^transform$/i }));

  // Preview shows both the original and the transformed text.
  await waitFor(() => {
    expect(screen.getByText(/The cat sat on the mat/i)).toBeInTheDocument();
    expect(screen.getByText(/feline reposed upon the rug/i)).toBeInTheDocument();
  });

  expect(mockTransform).toHaveBeenCalledWith('b1', 'c1', {
    content: '<p>The cat sat on the mat.</p>',
    target_style: 'professional',
  });

  await user.click(screen.getByRole('button', { name: /apply to chapter/i }));
  expect(onApply).toHaveBeenCalledWith('<p>The feline reposed upon the rug.</p>');
});

it('blocks transforming empty content without calling the API', async () => {
  const user = userEvent.setup();
  setup('<p></p>');

  await user.click(screen.getByRole('button', { name: /transform style/i }));
  await user.click(screen.getByRole('button', { name: /^transform$/i }));

  expect(await screen.findByText(/add some content/i)).toBeInTheDocument();
  expect(mockTransform).not.toHaveBeenCalled();
});

it('shows an error and returns to options when transformation fails', async () => {
  const user = userEvent.setup();
  mockTransform.mockRejectedValueOnce(new Error('AI service unavailable'));
  setup();

  await user.click(screen.getByRole('button', { name: /transform style/i }));
  await user.click(screen.getByRole('button', { name: /^transform$/i }));

  expect(await screen.findByText(/AI service unavailable/i)).toBeInTheDocument();
  // Still on the options step (Transform button visible again).
  expect(screen.getByRole('button', { name: /^transform$/i })).toBeInTheDocument();
});

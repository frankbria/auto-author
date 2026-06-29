import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VoiceEnhancer } from '@/components/chapters/VoiceEnhancer';
import { bookClient } from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  bookClient: {
    enhanceVoiceTranscription: jest.fn(),
  },
  default: { enhanceVoiceTranscription: jest.fn() },
}));

jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));

const mockCleanup = bookClient.enhanceVoiceTranscription as jest.Mock;

function setup(content = '<p>um so the cat you know sat on the mat</p>') {
  const onApply = jest.fn();
  render(
    <VoiceEnhancer
      bookId="b1"
      chapterId="c1"
      getCurrentContent={() => content}
      onApply={onApply}
    />
  );
  return { onApply };
}

beforeEach(() => jest.clearAllMocks());

it('renders the clean-up button', () => {
  setup();
  expect(screen.getByRole('button', { name: /clean up dictation/i })).toBeInTheDocument();
});

it('cleans up, previews raw vs cleaned, and applies to the editor', async () => {
  const user = userEvent.setup();
  mockCleanup.mockResolvedValueOnce({
    success: true,
    enhanced: '<p>The cat sat on the mat.</p>',
    metadata: { enhancement_label: 'Dictation Cleanup' },
  });
  const { onApply } = setup();

  await user.click(screen.getByRole('button', { name: /clean up dictation/i }));
  await user.click(screen.getByRole('button', { name: /^clean up$/i }));

  await waitFor(() => {
    expect(screen.getByText(/um so the cat/i)).toBeInTheDocument();
    expect(screen.getByText(/^The cat sat on the mat\.$/i)).toBeInTheDocument();
  });

  expect(mockCleanup).toHaveBeenCalledWith('b1', 'c1', {
    content: '<p>um so the cat you know sat on the mat</p>',
  });

  await user.click(screen.getByRole('button', { name: /apply to chapter/i }));
  expect(onApply).toHaveBeenCalledWith('<p>The cat sat on the mat.</p>');
});

it('blocks cleanup of empty content without calling the API', async () => {
  const user = userEvent.setup();
  setup('<p></p>');

  await user.click(screen.getByRole('button', { name: /clean up dictation/i }));
  await user.click(screen.getByRole('button', { name: /^clean up$/i }));

  expect(await screen.findByText(/dictate or add some text/i)).toBeInTheDocument();
  expect(mockCleanup).not.toHaveBeenCalled();
});

it('shows an error and returns to intro when cleanup fails', async () => {
  const user = userEvent.setup();
  mockCleanup.mockRejectedValueOnce(new Error('AI service unavailable'));
  setup();

  await user.click(screen.getByRole('button', { name: /clean up dictation/i }));
  await user.click(screen.getByRole('button', { name: /^clean up$/i }));

  expect(await screen.findByText(/AI service unavailable/i)).toBeInTheDocument();
  // Back on the intro step: the footer "Clean up" submit button is visible again.
  expect(screen.getByRole('button', { name: /^clean up$/i })).toBeInTheDocument();
});

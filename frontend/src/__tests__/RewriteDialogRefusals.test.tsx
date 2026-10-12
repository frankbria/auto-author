/**
 * What the three rewrite dialogs show when the backend refuses (#803).
 *
 * They used to print the thrown message, which was the status and the raw
 * body, and fire their own toast. A plan refusal never reached the Upgrade
 * notification and an exhausted allowance looked like any other failure.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StyleTransformer } from '@/components/chapters/StyleTransformer';
import { ContentEnhancer } from '@/components/chapters/ContentEnhancer';
import { VoiceEnhancer } from '@/components/chapters/VoiceEnhancer';
import { bookClient } from '@/lib/api/bookClient';
import { showErrorNotification } from '@/components/errors/ErrorNotification';
import { toast } from '@/lib/toast';

jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  bookClient: {
    transformChapterStyle: jest.fn(),
    enhanceChapterText: jest.fn(),
    enhanceVoiceTranscription: jest.fn(),
  },
}));

jest.mock('@/components/errors/ErrorNotification', () => ({
  showErrorNotification: jest.fn(),
}));

jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));

const props = {
  bookId: 'b1',
  chapterId: 'c1',
  getCurrentContent: () => '<p>The cat sat on the mat.</p>',
  onApply: jest.fn(),
};

type Driver = { call: jest.Mock; open: () => Promise<void> };

const DIALOGS: Array<[string, () => Driver]> = [
  [
    'Transform Style',
    () => {
      const user = userEvent.setup();
      render(<StyleTransformer {...props} />);
      return {
        call: bookClient.transformChapterStyle as jest.Mock,
        open: async () => {
          await user.click(screen.getByRole('button', { name: /transform style/i }));
          await user.click(screen.getByRole('button', { name: /^transform$/i }));
        },
      };
    },
  ],
  [
    'Enhance',
    () => {
      const user = userEvent.setup();
      render(<ContentEnhancer {...props} />);
      return {
        call: bookClient.enhanceChapterText as jest.Mock,
        open: async () => {
          await user.click(screen.getByRole('button', { name: /^enhance$/i }));
          const buttons = screen.getAllByRole('button', { name: /^enhance$/i });
          await user.click(buttons[buttons.length - 1]);
        },
      };
    },
  ],
  [
    'Clean up dictation',
    () => {
      const user = userEvent.setup();
      render(<VoiceEnhancer {...props} />);
      return {
        call: bookClient.enhanceVoiceTranscription as jest.Mock,
        open: async () => {
          await user.click(screen.getByRole('button', { name: /clean up dictation/i }));
          await user.click(screen.getByRole('button', { name: /^clean up$/i }));
        },
      };
    },
  ],
];

const refusal = (message: string, extra: Record<string, unknown>) => Object.assign(new Error(message), extra);

beforeEach(() => jest.clearAllMocks());

describe.each(DIALOGS)('%s', (_name, mount) => {
  it('sends a plan refusal (402) to the Upgrade notification and shows no JSON', async () => {
    const dialog = mount();
    dialog.call.mockRejectedValueOnce(refusal('Your plan does not include this feature.', { statusCode: 402 }));

    await dialog.open();

    expect(await screen.findByText(/does not include this feature/i)).toBeInTheDocument();
    expect(showErrorNotification).toHaveBeenCalledTimes(1);
    expect(showErrorNotification).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'entitlement', message: 'Upgrade required', retryable: false }),
      expect.anything()
    );
    expect(document.body.textContent).not.toMatch(/[{}]|402/);
    // One announcement, from the shared handler; no second toast from the dialog.
    expect(toast).not.toHaveBeenCalled();
  });

  it('shows an exhausted allowance (429 with its period) as a limit, with no retry', async () => {
    const quota = 'AI usage limit reached (10 generations per day on the free plan). It resets at midnight UTC.';
    const dialog = mount();
    dialog.call.mockRejectedValueOnce(refusal(quota, { statusCode: 429, quotaPeriod: 'day' }));

    await dialog.open();

    expect(await screen.findByText(quota)).toBeInTheDocument();
    expect(showErrorNotification).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'Daily AI limit reached', details: quota, retryable: false }),
      expect.anything()
    );
    expect(toast).not.toHaveBeenCalled();
  });
});

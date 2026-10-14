/**
 * Every place that puts AI output into the page as HTML cleans it first (#844).
 *
 * Five components render a model's answer, and four of them the chapter's own
 * text beside it, with dangerouslySetInnerHTML after DOMPurify.sanitize. Taking
 * the sanitize call out left every test green: nothing sent them anything
 * hostile, and one suite stood in for DOMPurify itself. Here each is sent the
 * same payload, through the API stand-in, and the page must keep the words and
 * lose the script, the event handler and the javascript: link.
 *
 * DOMPurify is not stood in for.
 */
import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StyleTransformer } from '@/components/chapters/StyleTransformer';
import { ContentEnhancer } from '@/components/chapters/ContentEnhancer';
import { VoiceEnhancer } from '@/components/chapters/VoiceEnhancer';
import { DraftGenerator } from '@/components/chapters/DraftGenerator';
import { DraftGenerationButton } from '@/components/chapters/questions/DraftGenerationButton';
import { bookClient } from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient', () => {
  const client = {
    transformChapterStyle: jest.fn(),
    enhanceChapterText: jest.fn(),
    enhanceVoiceTranscription: jest.fn(),
    getChapterQAResponses: jest.fn(),
    generateChapterDraftWithErrorHandling: jest.fn(),
  };
  return { __esModule: true, default: client, bookClient: client };
});
jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), { success: jest.fn(), error: jest.fn(), warning: jest.fn(), info: jest.fn() }),
}));

const HOSTILE =
  '<p>Words worth keeping.</p>' +
  '<img src="x" onerror="window.__owned = true">' +
  '<script>window.__owned = true</script>' +
  '<a href="javascript:window.__owned = true">a link</a>';

const api = bookClient as unknown as Record<string, jest.Mock>;
const metadata = { original_word_count: 3, transformed_word_count: 3, enhanced_word_count: 3 };
const draft = {
  success: true, draft: HOSTILE, suggestions: [],
  metadata: { word_count: 3, estimated_reading_time: 1, generated_at: '2026-10-14', model_used: 'm', writing_style: 'conversational', target_length: 2000, actual_length: 3 },
};
const answered = {
  responses: [1, 2, 3].map(n => ({ question: `Question ${n}?`, answer: `Answer ${n}.`, questionId: `q${n}`, status: 'completed' })),
  totalQuestions: 3, completedCount: 3, inProgressCount: 0,
};

type Renderer = { show: () => Promise<HTMLElement> };

const RENDERERS: Array<[string, () => Renderer]> = [
  ['StyleTransformer', () => {
    const user = userEvent.setup();
    api.transformChapterStyle.mockResolvedValue({ transformed: HOSTILE, metadata });
    render(<StyleTransformer bookId="b1" chapterId="c1" getCurrentContent={() => HOSTILE} onApply={jest.fn()} />);
    return { show: async () => {
      await user.click(screen.getByRole('button', { name: /transform style/i }));
      await user.click(screen.getByRole('button', { name: /^transform$/i }));
      return screen.findByRole('dialog');
    } };
  }],
  ['ContentEnhancer', () => {
    const user = userEvent.setup();
    api.enhanceChapterText.mockResolvedValue({ enhanced: HOSTILE, metadata });
    render(<ContentEnhancer bookId="b1" chapterId="c1" getCurrentContent={() => HOSTILE} onApply={jest.fn()} />);
    return { show: async () => {
      await user.click(screen.getByRole('button', { name: /^enhance$/i }));
      const buttons = screen.getAllByRole('button', { name: /^enhance$/i });
      await user.click(buttons[buttons.length - 1]);
      return screen.findByRole('dialog');
    } };
  }],
  ['VoiceEnhancer', () => {
    const user = userEvent.setup();
    api.enhanceVoiceTranscription.mockResolvedValue({ enhanced: HOSTILE, metadata });
    render(<VoiceEnhancer bookId="b1" chapterId="c1" getCurrentContent={() => HOSTILE} onApply={jest.fn()} />);
    return { show: async () => {
      await user.click(screen.getByRole('button', { name: /clean up dictation/i }));
      await user.click(screen.getByRole('button', { name: /^clean up$/i }));
      return screen.findByRole('dialog');
    } };
  }],
  ['DraftGenerator', () => {
    const user = userEvent.setup();
    api.getChapterQAResponses.mockResolvedValue(answered);
    api.generateChapterDraftWithErrorHandling.mockResolvedValue({ data: draft });
    render(<DraftGenerator bookId="b1" chapterId="c1" chapterTitle="Why Habits Stick" onDraftGenerated={jest.fn()} />);
    return { show: async () => {
      await user.click(screen.getByRole('button', { name: /generate ai draft/i }));
      await waitFor(() => expect(screen.getAllByDisplayValue('Answer 1.').length).toBeGreaterThan(0));
      await user.click(screen.getByRole('button', { name: /^generate draft$/i }));
      return screen.findByRole('dialog');
    } };
  }],
  ['DraftGenerationButton', () => {
    const user = userEvent.setup();
    api.getChapterQAResponses.mockResolvedValue(answered);
    api.generateChapterDraftWithErrorHandling.mockResolvedValue({ data: draft });
    render(<DraftGenerationButton bookId="b1" chapterId="c1" chapterTitle="Why Habits Stick" completedCount={3} totalQuestions={3} />);
    return { show: async () => {
      await user.click(screen.getByRole('button', { name: /generate draft from answers/i }));
      await user.click(screen.getByRole('button', { name: /^generate draft$/i }));
      return screen.findByRole('dialog');
    } };
  }],
];

beforeEach(() => {
  jest.clearAllMocks();
  delete (window as unknown as { __owned?: boolean }).__owned;
});

describe.each(RENDERERS)('%s, sent hostile HTML', (_name, mount) => {
  it('keeps the words and drops the script, the handler and the javascript: link', async () => {
    const dialog = await mount().show();

    await waitFor(() => expect(within(dialog).getAllByText('Words worth keeping.').length).toBeGreaterThan(0));
    expect(dialog.querySelectorAll('script')).toHaveLength(0);
    expect(dialog.querySelectorAll('[onerror]')).toHaveLength(0);
    expect(dialog.querySelectorAll('a[href^="javascript:" i]')).toHaveLength(0);
    expect((window as unknown as { __owned?: boolean }).__owned).toBeUndefined();
  });
});

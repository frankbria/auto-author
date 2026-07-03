/**
 * Regression tests for #64: stored user preferences are applied as defaults
 * across draft generation, the export dialog, and editor auto-save.
 */
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { DraftGenerator } from '@/components/chapters/DraftGenerator';
import DraftGenerationButton from '@/components/chapters/questions/DraftGenerationButton';
import { ExportOptionsModal } from '@/components/export/ExportOptionsModal';
import { ChapterEditor } from '@/components/chapters/ChapterEditor';
import bookClient from '@/lib/api/bookClient';
import { useUserPreferences } from '@/hooks/useUserPreferences';

jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    generateChapterDraft: jest.fn(),
    getExportFormats: jest.fn(),
    getChapterContent: jest.fn(),
    saveChapterContent: jest.fn(),
  },
  bookClient: {
    generateChapterDraft: jest.fn(),
    getQuestionsWithProgress: jest.fn(),
  },
}));

jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));

jest.mock('@/components/chapters/questions/QuestionContainer', () => ({
  __esModule: true,
  default: () => <div>Questions</div>,
}));

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;
// Globally stubbed in jest.setup.ts; give it values per test here.
const mockUseUserPreferences = useUserPreferences as jest.Mock;

describe('DraftGenerator default writing style', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('pre-selects the stored default style', async () => {
    mockUseUserPreferences.mockReturnValue({ default_writing_style: 'academic' });
    const user = userEvent.setup();
    render(
      <DraftGenerator bookId="b1" chapterId="c1" chapterTitle="Ch" />
    );
    await user.click(screen.getByRole('button', { name: /generate ai draft/i }));

    expect(screen.getByLabelText(/writing style/i)).toHaveValue('academic');
  });

  it('falls back to conversational without a stored preference', async () => {
    mockUseUserPreferences.mockReturnValue(null);
    const user = userEvent.setup();
    render(
      <DraftGenerator bookId="b1" chapterId="c1" chapterTitle="Ch" />
    );
    await user.click(screen.getByRole('button', { name: /generate ai draft/i }));

    expect(screen.getByLabelText(/writing style/i)).toHaveValue('conversational');
  });
});

describe('DraftGenerationButton default writing style', () => {
  it('pre-selects the stored default style', async () => {
    mockUseUserPreferences.mockReturnValue({ default_writing_style: 'creative' });
    const user = userEvent.setup();
    render(
      <DraftGenerationButton
        bookId="b1"
        chapterId="c1"
        chapterTitle="Ch"
        completedCount={5}
        totalQuestions={5}
      />
    );
    await user.click(screen.getByRole('button', { name: /generate draft/i }));

    expect(screen.getByLabelText(/writing style/i)).toHaveValue('creative');
  });
});

describe('ExportOptionsModal stored defaults', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (mockBookClient.getExportFormats as jest.Mock).mockResolvedValue({
      formats: [],
      book_stats: {
        total_chapters: 3,
        chapters_with_content: 2,
        total_word_count: 100,
        estimated_pages: 1,
      },
      templates: [],
    });
  });

  const renderModal = () =>
    render(
      <ExportOptionsModal
        bookId="b1"
        isOpen
        onOpenChange={jest.fn()}
        onExport={jest.fn()}
        bookTitle="Book"
      />
    );

  it('initializes format, page size, and empty-chapter toggle from preferences', async () => {
    mockUseUserPreferences.mockReturnValue({
      default_export_format: 'epub',
      default_page_size: 'A4',
      include_empty_chapters: true,
    });
    renderModal();

    await waitFor(() =>
      expect(screen.getByRole('radio', { name: /epub/i })).toBeChecked()
    );
    expect(screen.getByRole('switch', { name: /include empty chapters/i })).toBeChecked();
  });

  it('keeps shipped defaults when no preferences are stored', async () => {
    mockUseUserPreferences.mockReturnValue(null);
    renderModal();

    await waitFor(() =>
      expect(screen.getByRole('radio', { name: /pdf/i })).toBeChecked()
    );
    expect(
      screen.getByRole('switch', { name: /include empty chapters/i })
    ).not.toBeChecked();
  });
});

describe('ChapterEditor auto-save interval preference', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    jest.useFakeTimers();
    (mockBookClient.getChapterContent as jest.Mock).mockResolvedValue({
      content: '<p>Initial</p>',
    });
    (mockBookClient.saveChapterContent as jest.Mock).mockResolvedValue({ success: true });
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  const typeAndAdvance = async (ms: number) => {
    const user = userEvent.setup({ delay: null });
    render(
      <ChapterEditor bookId="b1" chapterId="c1" chapterTitle="Ch" initialContent="<p>Initial</p>" />
    );
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument());
    const editor = screen.getByRole('textbox');
    await user.clear(editor);
    await user.type(editor, 'New content');
    await act(async () => {
      jest.advanceTimersByTime(ms);
      await Promise.resolve();
    });
  };

  it('waits for the configured interval before auto-saving', async () => {
    mockUseUserPreferences.mockReturnValue({ auto_save_interval: 10 });
    await typeAndAdvance(3000);
    // 3s elapsed — the shipped default would have fired, the 10s preference must not
    expect(mockBookClient.saveChapterContent).not.toHaveBeenCalled();

    await act(async () => {
      jest.advanceTimersByTime(7000);
      await Promise.resolve();
    });
    await waitFor(() => expect(mockBookClient.saveChapterContent).toHaveBeenCalled());
  });

  it('uses the 3s default when the stored interval is invalid', async () => {
    mockUseUserPreferences.mockReturnValue({ auto_save_interval: 999 });
    await typeAndAdvance(3000);
    await waitFor(() => expect(mockBookClient.saveChapterContent).toHaveBeenCalled());
  });
});

import React, { Suspense } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ExportBookPage from '../page';
import { useSession } from '@/lib/auth-client';
import bookClient from '@/lib/api/bookClient';
import { toast } from '@/lib/toast';
import { createProgressTracker } from '@/lib/loading';

jest.mock('@/lib/auth-client');
jest.mock('@/lib/api/bookClient');
jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({ back: jest.fn(), push: jest.fn() })),
}));
jest.mock('@/components/loading', () => ({
  LoadingStateManager: ({ operation }: { operation: string }) => (
    <div data-testid="loading-state-manager">{operation}</div>
  ),
}));
jest.mock('@/lib/loading', () => ({
  createProgressTracker: jest.fn(() => () => ({
    progress: 50,
    estimatedTimeRemaining: 1000,
    elapsedTime: 1000,
    estimate: { min: 0, max: 0, average: 2000 },
  })),
}));

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

const FORMATS = {
  formats: [
    {
      format: 'pdf',
      name: 'PDF Document',
      description: 'Portable Document Format',
      extension: '.pdf',
      mime_type: 'application/pdf',
      available: true,
    },
    {
      format: 'docx',
      name: 'Word Document',
      description: 'Microsoft Word format',
      extension: '.docx',
      mime_type:
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      available: true,
    },
    {
      format: 'epub',
      name: 'EPUB Ebook',
      description: 'Standard eBook format',
      extension: '.epub',
      mime_type: 'application/epub+zip',
      available: true,
    },
    {
      format: 'markdown',
      name: 'Markdown Document',
      description: 'Plain-text Markdown',
      extension: '.md',
      mime_type: 'text/markdown',
      available: true,
    },
  ],
};

const CHAPTERS = {
  chapters: [
    { id: 'ch-1', title: 'Chapter One', status: 'draft', word_count: 1200 },
    { id: 'ch-2', title: 'Chapter Two', status: 'final', word_count: 800 },
  ],
};

// React's `use()` never un-suspends from a plain Promise.resolve() in this
// jest environment; a pre-fulfilled thenable lets it read the value synchronously.
function fulfilledParams<T>(value: T): Promise<T> {
  const p = Promise.resolve(value) as Promise<T> & { status: string; value: T };
  p.status = 'fulfilled';
  p.value = value;
  return p;
}

function renderPage() {
  return render(
    <Suspense fallback={null}>
      <ExportBookPage params={fulfilledParams({ bookId: 'book-1' })} />
    </Suspense>
  );
}

async function selectFormat(name: string | RegExp) {
  // The selected format's name also appears in the Export Summary; the
  // format card renders first in the DOM.
  const [card] = await screen.findAllByText(name);
  fireEvent.click(card);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useSession as jest.Mock).mockReturnValue({
    data: { user: { id: 'user-1', email: 'u@example.com' } },
  });
  mockBookClient.getBook = jest
    .fn()
    .mockResolvedValue({ id: 'book-1', title: 'My Great Book' } as any);
  mockBookClient.getExportFormats = jest.fn().mockResolvedValue(FORMATS as any);
  mockBookClient.getChaptersMetadata = jest
    .fn()
    .mockResolvedValue(CHAPTERS as any);
  mockBookClient.exportPDF = jest
    .fn()
    .mockResolvedValue(new Blob(['pdf'], { type: 'application/pdf' }));
  mockBookClient.exportDOCX = jest
    .fn()
    .mockResolvedValue(new Blob(['docx'], { type: 'application/docx' }));
  mockBookClient.exportEPUB = jest
    .fn()
    .mockResolvedValue(new Blob(['epub'], { type: 'application/epub+zip' }));
  mockBookClient.exportMarkdown = jest
    .fn()
    .mockResolvedValue(new Blob(['md'], { type: 'text/markdown' }));
});

describe('ExportBookPage format dispatch', () => {
  it('exports PDF with page size and include-empty options', async () => {
    renderPage();
    await selectFormat('PDF Document');
    fireEvent.click(screen.getByRole('button', { name: 'Export Book' }));
    await waitFor(() =>
      expect(mockBookClient.exportPDF).toHaveBeenCalledWith('book-1', {
        includeEmptyChapters: false,
        pageSize: 'letter',
      })
    );
    expect(await screen.findByText('Export Complete!')).toBeInTheDocument();
  });

  it('exports DOCX with include-empty option', async () => {
    renderPage();
    await selectFormat('Word Document');
    fireEvent.click(screen.getByRole('button', { name: 'Export Book' }));
    await waitFor(() =>
      expect(mockBookClient.exportDOCX).toHaveBeenCalledWith('book-1', {
        includeEmptyChapters: false,
      })
    );
  });

  it('exports EPUB instead of showing "not yet implemented" (#194)', async () => {
    renderPage();
    await selectFormat('EPUB Ebook');
    fireEvent.click(screen.getByRole('button', { name: 'Export Book' }));
    await waitFor(() =>
      expect(mockBookClient.exportEPUB).toHaveBeenCalledWith('book-1', {
        includeEmptyChapters: false,
      })
    );
    expect(toast.error).not.toHaveBeenCalled();
    expect(await screen.findByText('Export Complete!')).toBeInTheDocument();
  });

  it('exports Markdown instead of showing "not yet implemented" (#194)', async () => {
    renderPage();
    await selectFormat('Markdown Document');
    fireEvent.click(screen.getByRole('button', { name: 'Export Book' }));
    await waitFor(() =>
      expect(mockBookClient.exportMarkdown).toHaveBeenCalledWith('book-1', {
        includeEmptyChapters: false,
        multiFile: false,
      })
    );
    expect(toast.error).not.toHaveBeenCalled();
  });

  it('passes multiFile: true when the Markdown multi-file toggle is on', async () => {
    renderPage();
    await selectFormat('Markdown Document');
    fireEvent.click(screen.getByLabelText('Separate File Per Chapter'));
    fireEvent.click(screen.getByRole('button', { name: 'Export Book' }));
    await waitFor(() =>
      expect(mockBookClient.exportMarkdown).toHaveBeenCalledWith('book-1', {
        includeEmptyChapters: false,
        multiFile: true,
      })
    );
  });

  it('does not leak multiFile into an EPUB export after switching from Markdown', async () => {
    renderPage();
    await selectFormat('Markdown Document');
    fireEvent.click(screen.getByLabelText('Separate File Per Chapter'));
    await selectFormat('EPUB Ebook');
    fireEvent.click(screen.getByRole('button', { name: 'Export Book' }));
    await waitFor(() =>
      expect(mockBookClient.exportEPUB).toHaveBeenCalledWith('book-1', {
        includeEmptyChapters: false,
      })
    );
    expect(mockBookClient.exportMarkdown).not.toHaveBeenCalled();
  });

  it('still rejects an unknown format with an error toast', async () => {
    mockBookClient.getExportFormats = jest.fn().mockResolvedValue({
      formats: [
        {
          format: 'txt',
          name: 'Plain Text',
          description: 'Plain text',
          extension: '.txt',
          mime_type: 'text/plain',
          available: true,
        },
      ],
    } as any);
    renderPage();
    await selectFormat('Plain Text');
    fireEvent.click(screen.getByRole('button', { name: 'Export Book' }));
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith({
        title: 'This export format is not yet implemented',
      })
    );
  });

  it("surfaces the backend's userMessage when the export fails", async () => {
    const err = Object.assign(new Error('Export failed: 504'), {
      statusCode: 504,
      userMessage: 'The export timed out. Please try again shortly.',
    });
    mockBookClient.exportEPUB = jest.fn().mockRejectedValue(err);
    renderPage();
    await selectFormat('EPUB Ebook');
    fireEvent.click(screen.getByRole('button', { name: 'Export Book' }));
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith({
        title: 'The export timed out. Please try again shortly.',
      })
    );
  });

  it('falls back to the generic message when no userMessage is present', async () => {
    mockBookClient.exportEPUB = jest
      .fn()
      .mockRejectedValue(new Error('boom'));
    renderPage();
    await selectFormat('EPUB Ebook');
    fireEvent.click(screen.getByRole('button', { name: 'Export Book' }));
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith({
        title: 'Failed to export book. Please try again.',
      })
    );
  });
});

describe('ExportBookPage download filenames', () => {
  let anchors: HTMLAnchorElement[];

  beforeEach(() => {
    anchors = [];
    window.URL.createObjectURL = jest.fn(() => 'blob:mock');
    window.URL.revokeObjectURL = jest.fn();
    const origCreate = document.createElement.bind(document);
    jest
      .spyOn(document, 'createElement')
      .mockImplementation((tag: string, options?: ElementCreationOptions) => {
        const el = origCreate(tag, options);
        if (tag === 'a') anchors.push(el as HTMLAnchorElement);
        return el;
      });
    jest
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});
  });

  afterEach(() => {
    // Re-spying an unrestored spy recurses into itself on the next run.
    jest.restoreAllMocks();
  });

  async function exportAndDownload(formatName: string | RegExp) {
    await selectFormat(formatName);
    fireEvent.click(screen.getByRole('button', { name: 'Export Book' }));
    fireEvent.click(await screen.findByRole('button', { name: /Download File/ }));
  }

  it('downloads single-file Markdown as .md', async () => {
    renderPage();
    await exportAndDownload('Markdown Document');
    expect(anchors[anchors.length - 1].download).toBe('my_great_book.md');
  });

  it('downloads multi-file Markdown as .zip (blob is a ZIP archive)', async () => {
    renderPage();
    await selectFormat('Markdown Document');
    fireEvent.click(screen.getByLabelText('Separate File Per Chapter'));
    fireEvent.click(screen.getByRole('button', { name: 'Export Book' }));
    fireEvent.click(await screen.findByRole('button', { name: /Download File/ }));
    expect(anchors[anchors.length - 1].download).toBe('my_great_book.zip');
  });

  it('downloads EPUB as .epub', async () => {
    renderPage();
    await exportAndDownload('EPUB Ebook');
    expect(anchors[anchors.length - 1].download).toBe('my_great_book.epub');
  });

  it('downloads PDF as .pdf', async () => {
    renderPage();
    await exportAndDownload('PDF Document');
    expect(anchors[anchors.length - 1].download).toBe('my_great_book.pdf');
  });
});

describe('ExportBookPage per-format options UI', () => {
  it('EPUB shows include-empty toggle but no page size', async () => {
    renderPage();
    await selectFormat('EPUB Ebook');
    expect(screen.getByText('Include Empty Chapters')).toBeInTheDocument();
    expect(screen.queryByText('Page Size')).not.toBeInTheDocument();
  });

  it('Markdown shows include-empty and multi-file toggles', async () => {
    renderPage();
    await selectFormat('Markdown Document');
    expect(screen.getByText('Include Empty Chapters')).toBeInTheDocument();
    expect(screen.getByText('Separate File Per Chapter')).toBeInTheDocument();
  });

  it('PDF keeps page size options (regression)', async () => {
    renderPage();
    await selectFormat('PDF Document');
    expect(screen.getByText('Page Size')).toBeInTheDocument();
  });

  it('export summary reflects Markdown multi-file selection', async () => {
    renderPage();
    await selectFormat('Markdown Document');
    fireEvent.click(screen.getByLabelText('Separate File Per Chapter'));
    expect(screen.getByText('Separate file per chapter')).toBeInTheDocument();
  });
});

describe('ExportBookPage progress tracking', () => {
  it.each([
    ['EPUB Ebook', 'export.epub'],
    ['Markdown Document', 'export.markdown'],
    ['PDF Document', 'export.pdf'],
    ['Word Document', 'export.docx'],
  ])('uses the %s budget key %s while exporting', async (name, key) => {
    // Hold the export open so the isExporting state (and tracker) is observable
    let resolveBlob: (b: Blob) => void = () => {};
    const pending = new Promise<Blob>((r) => (resolveBlob = r));
    mockBookClient.exportEPUB = jest.fn().mockReturnValue(pending);
    mockBookClient.exportMarkdown = jest.fn().mockReturnValue(pending);
    mockBookClient.exportPDF = jest.fn().mockReturnValue(pending);
    mockBookClient.exportDOCX = jest.fn().mockReturnValue(pending);

    renderPage();
    await selectFormat(name);
    fireEvent.click(screen.getByRole('button', { name: 'Export Book' }));
    await waitFor(() =>
      expect(createProgressTracker).toHaveBeenCalledWith(
        key,
        expect.objectContaining({ wordCount: 2000, chapterCount: 2 })
      )
    );
    resolveBlob(new Blob(['x']));
  });
});

describe('ExportBookPage load failure', () => {
  it('shows an error toast when fetching export options fails', async () => {
    mockBookClient.getExportFormats = jest
      .fn()
      .mockRejectedValue(new Error('network'));
    renderPage();
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith({
        title: 'Failed to load export options. Please try again.',
      })
    );
  });
});

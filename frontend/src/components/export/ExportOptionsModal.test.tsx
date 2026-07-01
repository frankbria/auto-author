/**
 * Test suite for ExportOptionsModal component
 *
 * Following TDD: These tests define the expected behavior before implementation
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { ExportOptionsModal } from './ExportOptionsModal';
import bookClient from '@/lib/api/bookClient';

// Mock the performance tracking hook
jest.mock('@/hooks/usePerformanceTracking', () => ({
  usePerformanceTracking: () => ({
    trackOperation: async (_name: string, fn: () => any) => fn(),
  }),
}));

// Mock sonner toast
jest.mock('sonner', () => ({
  toast: {
    error: jest.fn(),
    success: jest.fn(),
  },
}));

// Mock the bookClient
jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    getExportFormats: jest.fn(() =>
      Promise.resolve({
        data: {
          book_stats: {
            total_chapters: 10,
            chapters_with_content: 8,
            total_word_count: 50000,
            estimated_pages: 200,
          },
        },
      })
    ),
  },
}));

describe('ExportOptionsModal', () => {
  const mockOnExport = jest.fn();
  const mockOnOpenChange = jest.fn();
  const mockBookId = 'test-book-id';

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render format selection options', async () => {
    render(
      <ExportOptionsModal
        bookId={mockBookId}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onExport={mockOnExport}
      />
    );

    // Wait for radio inputs to appear
    expect(await screen.findByLabelText(/PDF Document/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Word Document/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/EPUB Ebook/i)).toBeInTheDocument();
  });

  it('should call onExport with EPUB format (no pageSize)', async () => {
    render(
      <ExportOptionsModal
        bookId={mockBookId}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onExport={mockOnExport}
      />
    );

    fireEvent.click(await screen.findByLabelText(/EPUB Ebook/i));
    fireEvent.click(screen.getByRole('button', { name: /export epub/i }));

    expect(mockOnExport).toHaveBeenCalledWith({
      format: 'epub',
      includeEmptyChapters: false
    });
  });

  it('should hide page size options for EPUB', async () => {
    render(
      <ExportOptionsModal
        bookId={mockBookId}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onExport={mockOnExport}
      />
    );

    fireEvent.click(await screen.findByLabelText(/EPUB Ebook/i));

    expect(screen.queryByLabelText(/Letter.*US Standard/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/A4.*International Standard/i)).not.toBeInTheDocument();
  });

  it('should render a Markdown format option', async () => {
    render(
      <ExportOptionsModal
        bookId={mockBookId}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onExport={mockOnExport}
      />
    );

    expect(await screen.findByLabelText(/^Markdown$/i)).toBeInTheDocument();
  });

  it('should call onExport with Markdown format and multi-file flag', async () => {
    render(
      <ExportOptionsModal
        bookId={mockBookId}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onExport={mockOnExport}
      />
    );

    fireEvent.click(await screen.findByLabelText(/^Markdown$/i));
    // The multi-file switch only appears for Markdown.
    fireEvent.click(screen.getByLabelText(/Separate File Per Chapter/i));
    fireEvent.click(screen.getByRole('button', { name: /export markdown/i }));

    expect(mockOnExport).toHaveBeenCalledWith({
      format: 'markdown',
      includeEmptyChapters: false,
      markdownMultiFile: true,
    });
  });

  it('should hide the multi-file switch for non-Markdown formats', async () => {
    render(
      <ExportOptionsModal
        bookId={mockBookId}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onExport={mockOnExport}
      />
    );

    await screen.findByLabelText(/PDF Document/i);
    expect(screen.queryByLabelText(/Separate File Per Chapter/i)).not.toBeInTheDocument();
  });

  it('should call onExport with selected PDF format and default options', async () => {
    render(
      <ExportOptionsModal
        bookId={mockBookId}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onExport={mockOnExport}
      />
    );

    fireEvent.click(await screen.findByLabelText(/PDF Document/i));
    fireEvent.click(screen.getByRole('button', { name: /export pdf/i }));

    expect(mockOnExport).toHaveBeenCalledWith({
      format: 'pdf',
      includeEmptyChapters: false,
      pageSize: 'letter'
    });
  });

  it('should call onExport with DOCX format (no pageSize)', async () => {
    render(
      <ExportOptionsModal
        bookId={mockBookId}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onExport={mockOnExport}
      />
    );

    fireEvent.click(await screen.findByLabelText(/Word Document/i));
    fireEvent.click(screen.getByRole('button', { name: /export docx/i }));

    expect(mockOnExport).toHaveBeenCalledWith({
      format: 'docx',
      includeEmptyChapters: false
    });
  });

  it('should show page size options only for PDF', async () => {
    render(
      <ExportOptionsModal
        bookId={mockBookId}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onExport={mockOnExport}
      />
    );

    // PDF selected by default - page size should be visible
    expect(await screen.findByLabelText(/Letter.*US Standard/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/A4.*International Standard/i)).toBeInTheDocument();

    // Switch to DOCX
    fireEvent.click(screen.getByLabelText(/Word Document/i));

    // Page size options should not be visible
    expect(screen.queryByLabelText(/Letter.*US Standard/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/A4.*International Standard/i)).not.toBeInTheDocument();
  });

  it('should allow selecting A4 page size for PDF', async () => {
    render(
      <ExportOptionsModal
        bookId={mockBookId}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onExport={mockOnExport}
      />
    );

    fireEvent.click(await screen.findByLabelText(/PDF Document/i));
    fireEvent.click(screen.getByLabelText(/A4.*International Standard/i));
    fireEvent.click(screen.getByRole('button', { name: /export pdf/i }));

    expect(mockOnExport).toHaveBeenCalledWith({
      format: 'pdf',
      includeEmptyChapters: false,
      pageSize: 'A4'
    });
  });

  it('should call onOpenChange when cancel button clicked', async () => {
    render(
      <ExportOptionsModal
        bookId={mockBookId}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onExport={mockOnExport}
      />
    );

    fireEvent.click(await screen.findByRole('button', { name: /cancel/i }));

    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    expect(mockOnExport).not.toHaveBeenCalled();
  });

  // --- Template support (issue #59) ---

  const FORMATS_WITH_TEMPLATES = {
    data: {
      book_stats: {
        total_chapters: 10,
        chapters_with_content: 8,
        total_word_count: 50000,
        estimated_pages: 200,
      },
      templates: [
        {
          id: 'classic_fiction',
          name: 'Classic Fiction',
          description: '6x9 trade paperback.',
          category: 'fiction',
          best_for: 'Novels',
          page_size: '6x9',
          margins: { top: 0.75, bottom: 0.75, inside: 0.65, outside: 0.6 },
          font: { docx_font: 'Garamond', size: 11 },
          line_height: 1.3,
          first_line_indent: 0.2,
          header: { left: '{book_title}', right: '{author}' },
          footer: { center: '{page}' },
        },
      ],
    },
  };

  it('should render the template selector when templates are available', async () => {
    (bookClient.getExportFormats as jest.Mock).mockResolvedValueOnce(
      FORMATS_WITH_TEMPLATES
    );

    render(
      <ExportOptionsModal
        bookId={mockBookId}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onExport={mockOnExport}
      />
    );

    expect(await screen.findByTestId('template-selector')).toBeInTheDocument();
    expect(screen.getByLabelText('Classic Fiction')).toBeInTheDocument();
  });

  it('should include templateId in the export payload when a template is chosen', async () => {
    (bookClient.getExportFormats as jest.Mock).mockResolvedValueOnce(
      FORMATS_WITH_TEMPLATES
    );

    render(
      <ExportOptionsModal
        bookId={mockBookId}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onExport={mockOnExport}
      />
    );

    fireEvent.click(await screen.findByLabelText('Classic Fiction'));
    fireEvent.click(screen.getByRole('button', { name: /export pdf/i }));

    expect(mockOnExport).toHaveBeenCalledWith(
      expect.objectContaining({
        format: 'pdf',
        templateId: 'classic_fiction',
      })
    );
  });

  it('should not render when isOpen is false', () => {
    const { container } = render(
      <ExportOptionsModal
        bookId={mockBookId}
        isOpen={false}
        onOpenChange={mockOnOpenChange}
        onExport={mockOnExport}
      />
    );

    // Dialog should not be visible
    expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
  });
});

/**
 * Test suite for ExportOptionsModal component
 *
 * Following TDD: These tests define the expected behavior before implementation
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { ExportOptionsModal } from './ExportOptionsModal';

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

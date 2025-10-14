/**
 * Test suite for ExportOptionsModal component
 *
 * Following TDD: These tests define the expected behavior before implementation
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { ExportOptionsModal } from './ExportOptionsModal';

describe('ExportOptionsModal', () => {
  const mockOnExport = jest.fn();
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render format selection options', () => {
    render(
      <ExportOptionsModal
        isOpen={true}
        onExport={mockOnExport}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByLabelText('PDF')).toBeInTheDocument();
    expect(screen.getByLabelText('DOCX')).toBeInTheDocument();
  });

  it('should call onExport with selected PDF format and default options', () => {
    render(
      <ExportOptionsModal
        isOpen={true}
        onExport={mockOnExport}
        onCancel={mockOnCancel}
      />
    );

    fireEvent.click(screen.getByLabelText('PDF'));
    fireEvent.click(screen.getByRole('button', { name: /export/i }));

    expect(mockOnExport).toHaveBeenCalledWith({
      format: 'pdf',
      includeEmptyChapters: true,
      pageSize: 'letter'
    });
  });

  it('should call onExport with DOCX format (no pageSize)', () => {
    render(
      <ExportOptionsModal
        isOpen={true}
        onExport={mockOnExport}
        onCancel={mockOnCancel}
      />
    );

    fireEvent.click(screen.getByLabelText('DOCX'));
    fireEvent.click(screen.getByRole('button', { name: /export/i }));

    expect(mockOnExport).toHaveBeenCalledWith({
      format: 'docx',
      includeEmptyChapters: true
    });
  });

  it('should show page size options only for PDF', () => {
    const { rerender } = render(
      <ExportOptionsModal
        isOpen={true}
        onExport={mockOnExport}
        onCancel={mockOnCancel}
      />
    );

    // PDF selected by default - page size should be visible
    expect(screen.getByLabelText(/letter/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/a4/i)).toBeInTheDocument();

    // Switch to DOCX
    fireEvent.click(screen.getByLabelText('DOCX'));

    // Page size options should not be visible
    expect(screen.queryByLabelText(/letter/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/a4/i)).not.toBeInTheDocument();
  });

  it('should allow selecting A4 page size for PDF', () => {
    render(
      <ExportOptionsModal
        isOpen={true}
        onExport={mockOnExport}
        onCancel={mockOnCancel}
      />
    );

    fireEvent.click(screen.getByLabelText('PDF'));
    fireEvent.click(screen.getByLabelText(/a4/i));
    fireEvent.click(screen.getByRole('button', { name: /export/i }));

    expect(mockOnExport).toHaveBeenCalledWith({
      format: 'pdf',
      includeEmptyChapters: true,
      pageSize: 'a4'
    });
  });

  it('should call onCancel when cancel button clicked', () => {
    render(
      <ExportOptionsModal
        isOpen={true}
        onExport={mockOnExport}
        onCancel={mockOnCancel}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
    expect(mockOnExport).not.toHaveBeenCalled();
  });

  it('should not render when isOpen is false', () => {
    const { container } = render(
      <ExportOptionsModal
        isOpen={false}
        onExport={mockOnExport}
        onCancel={mockOnCancel}
      />
    );

    // Dialog should not be visible
    expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
  });
});

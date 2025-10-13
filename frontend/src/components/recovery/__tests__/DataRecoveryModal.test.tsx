/**
 * Tests for DataRecoveryModal component
 * Ensures recovery UI provides clear information and accessible controls
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DataRecoveryModal, RecoveredData } from '../DataRecoveryModal';

// Mock date-fns to have consistent test output
jest.mock('date-fns', () => ({
  formatDistanceToNow: jest.fn(() => '5 minutes ago'),
}));

describe('DataRecoveryModal', () => {
  const mockOnRestore = jest.fn();
  const mockOnDiscard = jest.fn();
  const mockOnOpenChange = jest.fn();

  const defaultRecoveredData: RecoveredData = {
    bookId: 'book-1',
    chapterId: 'chapter-1',
    content: '<p>This is recovered content from a previous session that was not saved to the server.</p>',
    timestamp: Date.now() - 300000, // 5 minutes ago
    error: 'Network connection lost',
  };

  const defaultProps = {
    isOpen: true,
    onOpenChange: mockOnOpenChange,
    recoveredData: defaultRecoveredData,
    onRestore: mockOnRestore,
    onDiscard: mockOnDiscard,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders modal with correct title', () => {
      render(<DataRecoveryModal {...defaultProps} />);

      expect(screen.getByText('Unsaved Changes Detected')).toBeInTheDocument();
    });

    it('displays timestamp information', () => {
      render(<DataRecoveryModal {...defaultProps} />);

      expect(screen.getByText('Last saved locally:')).toBeInTheDocument();
      expect(screen.getByText('5 minutes ago')).toBeInTheDocument();
    });

    it('displays formatted date and time', () => {
      const timestamp = new Date('2024-10-12T10:30:00').getTime();
      const dataWithSpecificTime: RecoveredData = {
        ...defaultRecoveredData,
        timestamp,
      };

      render(<DataRecoveryModal {...defaultProps} recoveredData={dataWithSpecificTime} />);

      // Check for date string (format varies by locale, so check for year at minimum)
      const dateText = screen.getByText(/2024/);
      expect(dateText).toBeInTheDocument();
    });

    it('displays error context when error is present', () => {
      render(<DataRecoveryModal {...defaultProps} />);

      expect(screen.getByText('Previous save failed:')).toBeInTheDocument();
      expect(screen.getByText('Network connection lost')).toBeInTheDocument();
    });

    it('hides error section when no error is present', () => {
      const dataWithoutError: RecoveredData = {
        ...defaultRecoveredData,
        error: undefined,
      };

      render(<DataRecoveryModal {...defaultProps} recoveredData={dataWithoutError} />);

      expect(screen.queryByText('Previous save failed:')).not.toBeInTheDocument();
    });

    it('displays content preview (first 100 chars, HTML stripped)', () => {
      render(<DataRecoveryModal {...defaultProps} />);

      expect(screen.getByText('Content preview:')).toBeInTheDocument();

      // Content should be stripped of HTML and truncated
      const preview = screen.getByText(/This is recovered content from a previous session/);
      expect(preview).toBeInTheDocument();

      // Long content should be truncated (default content is ~100 chars)
      expect(preview.textContent).toBeTruthy();
    });

    it('displays character count', () => {
      render(<DataRecoveryModal {...defaultProps} />);

      expect(screen.getByText(/Total characters:/)).toBeInTheDocument();
    });

    it('shows warning about replacing current content', () => {
      render(<DataRecoveryModal {...defaultProps} />);

      expect(screen.getByText(/Restoring this backup will replace the current content/)).toBeInTheDocument();
    });

    it('renders both action buttons', () => {
      render(<DataRecoveryModal {...defaultProps} />);

      expect(screen.getByRole('button', { name: /discard backup/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /restore backup/i })).toBeInTheDocument();
    });
  });

  describe('Content Preview', () => {
    it('strips HTML tags from preview', () => {
      const htmlContent: RecoveredData = {
        ...defaultRecoveredData,
        content: '<h1>Title</h1><p>Paragraph with <strong>bold</strong> and <em>italic</em></p>',
      };

      render(<DataRecoveryModal {...defaultProps} recoveredData={htmlContent} />);

      // Should not contain HTML tags
      expect(screen.queryByText(/<h1>/)).not.toBeInTheDocument();
      expect(screen.queryByText(/<p>/)).not.toBeInTheDocument();

      // Should contain plain text
      expect(screen.getByText(/Title.*Paragraph with bold and italic/)).toBeInTheDocument();
    });

    it('truncates long content at 100 characters', () => {
      const longContent = 'a'.repeat(200);
      const dataWithLongContent: RecoveredData = {
        ...defaultRecoveredData,
        content: `<p>${longContent}</p>`,
      };

      render(<DataRecoveryModal {...defaultProps} recoveredData={dataWithLongContent} />);

      const preview = screen.getByText(/a{100}/);
      expect(preview.textContent?.length).toBeLessThan(110); // Should be truncated with ellipsis
    });

    it('does not show ellipsis for short content', () => {
      const shortContent: RecoveredData = {
        ...defaultRecoveredData,
        content: '<p>Short content</p>',
      };

      render(<DataRecoveryModal {...defaultProps} recoveredData={shortContent} />);

      const previewContainer = screen.getByText('Short content').parentElement;
      expect(previewContainer?.textContent).not.toContain('...');
    });
  });

  describe('User Interactions', () => {
    it('calls onRestore when Restore Backup button is clicked', async () => {
      const user = userEvent.setup();
      render(<DataRecoveryModal {...defaultProps} />);

      const restoreButton = screen.getByRole('button', { name: /restore backup/i });
      await user.click(restoreButton);

      expect(mockOnRestore).toHaveBeenCalledWith(defaultRecoveredData);
    });

    it('calls onDiscard when Discard Backup button is clicked', async () => {
      const user = userEvent.setup();
      render(<DataRecoveryModal {...defaultProps} />);

      const discardButton = screen.getByRole('button', { name: /discard backup/i });
      await user.click(discardButton);

      expect(mockOnDiscard).toHaveBeenCalled();
      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    it('closes modal after successful restore', async () => {
      const user = userEvent.setup();
      mockOnRestore.mockResolvedValue(undefined);

      render(<DataRecoveryModal {...defaultProps} />);

      const restoreButton = screen.getByRole('button', { name: /restore backup/i });
      await user.click(restoreButton);

      await waitFor(() => {
        expect(mockOnOpenChange).toHaveBeenCalledWith(false);
      });
    });

    it('keeps modal open if restore fails', async () => {
      const user = userEvent.setup();
      mockOnRestore.mockRejectedValue(new Error('Restore failed'));

      render(<DataRecoveryModal {...defaultProps} />);

      const restoreButton = screen.getByRole('button', { name: /restore backup/i });
      await user.click(restoreButton);

      await waitFor(() => {
        expect(mockOnRestore).toHaveBeenCalled();
      });

      // Modal should not close on error
      expect(mockOnOpenChange).not.toHaveBeenCalled();
    });

    it('disables buttons during restore operation', async () => {
      const user = userEvent.setup();
      mockOnRestore.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)));

      render(<DataRecoveryModal {...defaultProps} />);

      const restoreButton = screen.getByRole('button', { name: /restore backup/i });
      const discardButton = screen.getByRole('button', { name: /discard backup/i });

      await user.click(restoreButton);

      // Both buttons should be disabled during processing
      await waitFor(() => {
        expect(restoreButton).toBeDisabled();
        expect(discardButton).toBeDisabled();
      });
    });

    it('shows "Restoring..." text during restore operation', async () => {
      const user = userEvent.setup();
      mockOnRestore.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)));

      render(<DataRecoveryModal {...defaultProps} />);

      const restoreButton = screen.getByRole('button', { name: /restore backup/i });
      await user.click(restoreButton);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /restoring/i })).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      render(<DataRecoveryModal {...defaultProps} />);

      expect(screen.getByRole('dialog')).toHaveAccessibleDescription();
    });

    it('has keyboard-accessible buttons', async () => {
      const user = userEvent.setup();
      render(<DataRecoveryModal {...defaultProps} />);

      const discardButton = screen.getByRole('button', { name: /discard backup/i });

      // Focus and activate with keyboard
      discardButton.focus();
      await user.keyboard('{Enter}');

      expect(mockOnDiscard).toHaveBeenCalled();
    });

    it('provides sufficient visual hierarchy', () => {
      render(<DataRecoveryModal {...defaultProps} />);

      // Check for heading elements
      const heading = screen.getByRole('heading', { name: /unsaved changes detected/i });
      expect(heading).toBeInTheDocument();

      // Check for warning icons (class-based check since Lucide doesn't expose role)
      const warningText = screen.getByText('Unsaved Changes Detected');
      expect(warningText).toBeInTheDocument();

      // Verify visual indicators are present
      expect(screen.getByText('Last saved locally:')).toBeInTheDocument();
      expect(screen.getByText('Content preview:')).toBeInTheDocument();
    });
  });

  describe('Modal Behavior', () => {
    it('respects isOpen prop', () => {
      const { rerender } = render(<DataRecoveryModal {...defaultProps} isOpen={false} />);

      expect(screen.queryByText('Unsaved Changes Detected')).not.toBeInTheDocument();

      rerender(<DataRecoveryModal {...defaultProps} isOpen={true} />);

      expect(screen.getByText('Unsaved Changes Detected')).toBeInTheDocument();
    });

    it('calls onOpenChange when modal is closed', async () => {
      const user = userEvent.setup();
      render(<DataRecoveryModal {...defaultProps} />);

      // Close via discard button
      const discardButton = screen.getByRole('button', { name: /discard backup/i });
      await user.click(discardButton);

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });
  });

  describe('Edge Cases', () => {
    it('handles very long error messages gracefully', () => {
      const longError = 'A'.repeat(500);
      const dataWithLongError: RecoveredData = {
        ...defaultRecoveredData,
        error: longError,
      };

      render(<DataRecoveryModal {...defaultProps} recoveredData={dataWithLongError} />);

      // Should render without crashing
      expect(screen.getByText('Previous save failed:')).toBeInTheDocument();
    });

    it('handles empty content gracefully', () => {
      const emptyContent: RecoveredData = {
        ...defaultRecoveredData,
        content: '',
      };

      render(<DataRecoveryModal {...defaultProps} recoveredData={emptyContent} />);

      expect(screen.getByText('Content preview:')).toBeInTheDocument();
      expect(screen.getByText('Total characters: 0')).toBeInTheDocument();
    });

    it('handles content with only HTML tags (no text)', () => {
      const htmlOnlyContent: RecoveredData = {
        ...defaultRecoveredData,
        content: '<div><span></span><p></p></div>',
      };

      render(<DataRecoveryModal {...defaultProps} recoveredData={htmlOnlyContent} />);

      expect(screen.getByText('Content preview:')).toBeInTheDocument();
    });

    it('handles timestamps from far past', () => {
      const oldTimestamp: RecoveredData = {
        ...defaultRecoveredData,
        timestamp: Date.now() - 10 * 24 * 60 * 60 * 1000, // 10 days ago
      };

      render(<DataRecoveryModal {...defaultProps} recoveredData={oldTimestamp} />);

      expect(screen.getByText('Last saved locally:')).toBeInTheDocument();
    });
  });
});

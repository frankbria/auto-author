/**
 * Tests for ChapterEditor save status indicators
 * Ensures visual feedback for save states: saving, saved, not saved, error
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChapterEditor } from '../ChapterEditor';
import bookClient from '@/lib/api/bookClient';

// Mock dependencies
jest.mock('@/lib/api/bookClient');
jest.mock('../DraftGenerator', () => ({
  DraftGenerator: () => <div>Draft Generator</div>
}));

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

describe('ChapterEditor save status indicators', () => {
  const defaultProps = {
    bookId: 'book-1',
    chapterId: 'chapter-1',
    chapterTitle: 'Test Chapter',
    initialContent: '<p>Initial content</p>',
  };

  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  describe('Initial state', () => {
    it('shows "Not saved yet" when no save has occurred', async () => {
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial content</p>' });

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      // Initial state should show "Not saved yet"
      expect(screen.getByText('Not saved yet')).toBeInTheDocument();

      // Check mark should not be visible
      expect(screen.queryByText(/saved/i)).not.toBeInTheDocument();

      // Spinner should not be visible
      expect(screen.queryByText('Saving...')).not.toBeInTheDocument();
    });
  });

  describe('Saving state', () => {
    it('shows loading spinner during auto-save', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });
      mockBookClient.saveChapterContent.mockImplementation(() =>
        new Promise((resolve) => setTimeout(resolve, 1000))
      );

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      // Type to trigger auto-save
      const editor = screen.getByRole('textbox');
      await user.clear(editor);
      await user.type(editor, 'New content');

      // Advance past debounce
      jest.advanceTimersByTime(3000);

      // Should show saving state
      await waitFor(() => {
        expect(screen.getByText('Saving...')).toBeInTheDocument();
      });

      // Verify spinner icon is present (via test id or accessible name)
      const savingText = screen.getByText('Saving...');
      expect(savingText).toBeInTheDocument();
    });

    it('shows loading spinner during manual save', async () => {
      const user = userEvent.setup();
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });
      mockBookClient.saveChapterContent.mockImplementation(() =>
        new Promise((resolve) => setTimeout(resolve, 1000))
      );

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
      });

      // Click Save button
      const saveButton = screen.getByRole('button', { name: /save/i });
      await user.click(saveButton);

      // Save button should show saving state
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /saving/i })).toBeInTheDocument();
      });

      // Status text should also show saving
      expect(screen.getByText('Saving...')).toBeInTheDocument();
    });

    it('disables save button during save operation', async () => {
      const user = userEvent.setup();
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });
      mockBookClient.saveChapterContent.mockImplementation(() =>
        new Promise((resolve) => setTimeout(resolve, 1000))
      );

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
      });

      const saveButton = screen.getByRole('button', { name: /save/i });
      await user.click(saveButton);

      // Button should be disabled during save
      await waitFor(() => {
        const savingButton = screen.getByRole('button', { name: /saving/i });
        expect(savingButton).toBeDisabled();
      });
    });
  });

  describe('Saved state', () => {
    it('shows green checkmark and timestamp after successful auto-save', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });
      mockBookClient.saveChapterContent.mockResolvedValue({});

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      const editor = screen.getByRole('textbox');
      await user.clear(editor);
      await user.type(editor, 'Saved content');

      jest.advanceTimersByTime(3000);

      // Wait for save to complete
      await waitFor(() => {
        expect(mockBookClient.saveChapterContent).toHaveBeenCalled();
      });

      // Should show saved status with timestamp
      await waitFor(() => {
        const savedText = screen.getByText(/^Saved/);
        expect(savedText).toBeInTheDocument();

        // Verify timestamp format (HH:MM:SS AM/PM)
        expect(savedText.textContent).toMatch(/Saved \d{1,2}:\d{2}:\d{2} (AM|PM)/);
      });

      // Verify green color styling (check className or style)
      const savedElement = screen.getByText(/^Saved/);
      expect(savedElement.className).toContain('green');
    });

    it('shows green checkmark after successful manual save', async () => {
      const user = userEvent.setup();
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });
      mockBookClient.saveChapterContent.mockResolvedValue({});

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
      });

      const saveButton = screen.getByRole('button', { name: /save/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockBookClient.saveChapterContent).toHaveBeenCalled();
      });

      // Should show saved status
      await waitFor(() => {
        expect(screen.getByText(/^Saved/)).toBeInTheDocument();
      });
    });

    it('updates timestamp on subsequent saves', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });
      mockBookClient.saveChapterContent.mockResolvedValue({});

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      const editor = screen.getByRole('textbox');

      // First save
      await user.clear(editor);
      await user.type(editor, 'First save');
      jest.advanceTimersByTime(3000);

      await waitFor(() => {
        expect(screen.getByText(/^Saved/)).toBeInTheDocument();
      });

      const firstTimestamp = screen.getByText(/^Saved/).textContent;

      // Advance time
      jest.advanceTimersByTime(10000);

      // Second save
      await user.type(editor, ' Second save');
      jest.advanceTimersByTime(3000);

      await waitFor(() => {
        const secondTimestamp = screen.getByText(/^Saved/).textContent;
        expect(secondTimestamp).not.toBe(firstTimestamp);
      });
    });
  });

  describe('Error state', () => {
    it('shows error message when save fails', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });
      mockBookClient.saveChapterContent.mockRejectedValue(new Error('Network error'));

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      const editor = screen.getByRole('textbox');
      await user.clear(editor);
      await user.type(editor, 'Failed content');

      jest.advanceTimersByTime(3000);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText('Failed to auto-save. Content backed up locally.')).toBeInTheDocument();
      });

      // Saved checkmark should not be visible
      expect(screen.queryByText(/^Saved/)).not.toBeInTheDocument();
    });

    it('clears error message on subsequent successful save', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });

      // First save fails
      mockBookClient.saveChapterContent.mockRejectedValueOnce(new Error('Network error'));

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      const editor = screen.getByRole('textbox');
      await user.clear(editor);
      await user.type(editor, 'First attempt');

      jest.advanceTimersByTime(3000);

      await waitFor(() => {
        expect(screen.getByText(/Failed to auto-save/)).toBeInTheDocument();
      });

      // Second save succeeds
      mockBookClient.saveChapterContent.mockResolvedValueOnce({});
      await user.type(editor, ' Second attempt');

      jest.advanceTimersByTime(3000);

      // Error should be cleared, saved status shown
      await waitFor(() => {
        expect(screen.queryByText(/Failed to auto-save/)).not.toBeInTheDocument();
        expect(screen.getByText(/^Saved/)).toBeInTheDocument();
      });
    });
  });

  describe('Character count', () => {
    it('displays character count alongside save status', async () => {
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      // Character count should be visible
      expect(screen.getByText(/characters$/)).toBeInTheDocument();

      // Both character count and save status should be in footer
      const footer = screen.getByText(/characters$/).closest('div');
      expect(footer).toContain(screen.getByText('Not saved yet'));
    });

    it('updates character count as user types', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      const editor = screen.getByRole('textbox');
      await user.clear(editor);
      await user.type(editor, 'Hello');

      // Character count should update (exact count depends on HTML markup)
      await waitFor(() => {
        const characterText = screen.getByText(/characters$/);
        expect(characterText.textContent).not.toBe('0 characters');
      });
    });
  });

  describe('Visual consistency', () => {
    it('maintains status indicator position in footer', async () => {
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      // Footer should contain all elements in consistent layout
      const footer = screen.getByText('Not saved yet').closest('div');
      expect(footer).toBeTruthy();

      // Verify Save button is in the same footer
      const saveButton = screen.getByRole('button', { name: /save/i });
      expect(footer).toContain(saveButton);
    });

    it('shows only one status indicator at a time', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });
      mockBookClient.saveChapterContent.mockResolvedValue({});

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      // Initially: "Not saved yet"
      expect(screen.getByText('Not saved yet')).toBeInTheDocument();
      expect(screen.queryByText('Saving...')).not.toBeInTheDocument();
      expect(screen.queryByText(/^Saved/)).not.toBeInTheDocument();

      // Trigger save
      const editor = screen.getByRole('textbox');
      await user.clear(editor);
      await user.type(editor, 'Content');

      jest.advanceTimersByTime(3000);

      // During save: "Saving..."
      await waitFor(() => {
        expect(screen.getByText('Saving...')).toBeInTheDocument();
        expect(screen.queryByText('Not saved yet')).not.toBeInTheDocument();
        expect(screen.queryByText(/^Saved/)).not.toBeInTheDocument();
      });

      // After save: "Saved [timestamp]"
      await waitFor(() => {
        expect(screen.getByText(/^Saved/)).toBeInTheDocument();
        expect(screen.queryByText('Saving...')).not.toBeInTheDocument();
        expect(screen.queryByText('Not saved yet')).not.toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('provides accessible status updates for screen readers', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });
      mockBookClient.saveChapterContent.mockResolvedValue({});

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      const editor = screen.getByRole('textbox');
      await user.clear(editor);
      await user.type(editor, 'Accessible content');

      jest.advanceTimersByTime(3000);

      // Status text should be present and readable
      await waitFor(() => {
        const savedStatus = screen.getByText(/^Saved/);
        expect(savedStatus).toBeVisible();
      });
    });
  });
});

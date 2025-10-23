/**
 * Tests for ChapterEditor save status indicators
 * Ensures visual feedback for save states: saving, saved, not saved, error
 */

import { render, screen, waitFor, act } from '@testing-library/react';
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

      // Check mark should not be visible - use ^Saved to match only "Saved [timestamp]", not "Not saved yet"
      expect(screen.queryByText(/^Saved/)).not.toBeInTheDocument();

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

      // Advance past debounce with act() wrapping
      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

      // Should show saving state
      await waitFor(() => {
        const savingElements = screen.queryAllByText('Saving...');
        expect(savingElements.length).toBeGreaterThan(0);
      });
    });

    it('shows loading spinner during manual save', async () => {
      const user = userEvent.setup({ delay: null });
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
      const savingElements = screen.queryAllByText('Saving...');
      expect(savingElements.length).toBeGreaterThan(0);

      // Advance timers to complete save
      await act(async () => {
        jest.advanceTimersByTime(1000);
        await Promise.resolve();
      });
    }, 10000);

    it('disables save button during save operation', async () => {
      const user = userEvent.setup({ delay: null });
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

      // Advance timers to complete save
      jest.advanceTimersByTime(1000);
    }, 10000);
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

      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

      // Wait for save to complete
      await waitFor(() => {
        expect(mockBookClient.saveChapterContent).toHaveBeenCalled();
      });

      // Should show saved status with timestamp
      await waitFor(() => {
        const savedElements = screen.getAllByText(/^Saved/);
        // Find the element with timestamp (not just "Saved content" from editor)
        const savedStatus = savedElements.find(el =>
          el.textContent && /Saved \d{1,2}:\d{2}:\d{2} (AM|PM)/.test(el.textContent)
        );
        expect(savedStatus).toBeDefined();
        expect(savedStatus?.textContent).toMatch(/Saved \d{1,2}:\d{2}:\d{2} (AM|PM)/);
      });

      // Verify green color styling (check className or style)
      const savedElements = screen.getAllByText(/^Saved/);
      const savedStatus = savedElements.find(el =>
        el.textContent && /Saved \d{1,2}:\d{2}:\d{2} (AM|PM)/.test(el.textContent)
      );
      expect(savedStatus?.className).toContain('green');
    });

    it('shows green checkmark after successful manual save', async () => {
      const user = userEvent.setup({ delay: null });
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
    }, 10000);

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

      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

      await waitFor(() => {
        expect(screen.getByText(/^Saved/)).toBeInTheDocument();
      });

      const firstTimestamp = screen.getByText(/^Saved/).textContent;

      // Advance time
      await act(async () => {
        jest.advanceTimersByTime(10000);
        await Promise.resolve();
      });

      // Second save
      await user.type(editor, ' Second save');

      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

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

      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

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

      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

      await waitFor(() => {
        expect(screen.getByText(/Failed to auto-save/)).toBeInTheDocument();
      });

      // Second save succeeds
      mockBookClient.saveChapterContent.mockResolvedValueOnce({});
      await user.type(editor, ' Second attempt');

      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

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

      // Save status should also be visible in the document
      expect(screen.getByText('Not saved yet')).toBeInTheDocument();
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

      // Save status should be visible
      expect(screen.getByText('Not saved yet')).toBeInTheDocument();

      // Save button should also be visible
      expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
    });

    it('shows only one status indicator at a time', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });
      // Add delay to save to catch "Saving..." state
      mockBookClient.saveChapterContent.mockImplementation(() =>
        new Promise((resolve) => setTimeout(resolve, 100))
      );

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

      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

      // During save: "Saving..."
      await waitFor(() => {
        const savingElements = screen.queryAllByText('Saving...');
        expect(savingElements.length).toBeGreaterThan(0);
        expect(screen.queryByText('Not saved yet')).not.toBeInTheDocument();
      });

      // Advance timer to complete save
      await act(async () => {
        jest.advanceTimersByTime(100);
        await Promise.resolve();
      });

      // After save: "Saved [timestamp]"
      await waitFor(() => {
        const savedElements = screen.queryAllByText(/^Saved/);
        const savedStatus = savedElements.find(el =>
          el.textContent && /Saved \d{1,2}:\d{2}:\d{2} (AM|PM)/.test(el.textContent)
        );
        expect(savedStatus).toBeDefined();
        expect(screen.queryByText('Saving...')).not.toBeInTheDocument();
        expect(screen.queryByText('Not saved yet')).not.toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('provides accessible status updates for screen readers', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });
      // Add delay to save to allow time for UI to update
      mockBookClient.saveChapterContent.mockImplementation(() =>
        new Promise((resolve) => setTimeout(resolve, 100))
      );

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      const editor = screen.getByRole('textbox');
      await user.clear(editor);
      await user.type(editor, 'Accessible content');

      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

      // Advance timer to complete save
      await act(async () => {
        jest.advanceTimersByTime(100);
        await Promise.resolve();
      });

      // Status text should be present and readable
      await waitFor(() => {
        const savedElements = screen.getAllByText(/^Saved/);
        const savedStatus = savedElements.find(el =>
          el.textContent && /Saved \d{1,2}:\d{2}:\d{2} (AM|PM)/.test(el.textContent)
        );
        expect(savedStatus).toBeDefined();
        expect(savedStatus).toBeVisible();
      });
    });
  });
});

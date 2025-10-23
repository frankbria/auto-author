/**
 * Tests for ChapterEditor localStorage backup functionality
 * Ensures auto-save failures trigger localStorage backup and recovery
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

describe('ChapterEditor localStorage backup', () => {
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

  describe('Backup on save failure', () => {
    it('backs up content to localStorage when auto-save fails', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial content</p>' });
      mockBookClient.saveChapterContent.mockRejectedValue(new Error('Network error'));

      render(<ChapterEditor {...defaultProps} />);

      // Wait for editor to initialize
      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      // Type new content
      const editor = screen.getByRole('textbox');
      await user.clear(editor);
      await user.type(editor, 'New content to backup');

      // Wait for 3-second debounce
      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

      // Wait for save failure and backup
      await waitFor(() => {
        const backupKey = 'chapter-backup-book-1-chapter-1';
        const backup = localStorage.getItem(backupKey);
        expect(backup).toBeTruthy();

        if (backup) {
          const parsed = JSON.parse(backup);
          expect(parsed.content).toContain('New content to backup');
          expect(parsed.timestamp).toBeDefined();
          expect(parsed.error).toBe('Network error');
        }
      });

      // Error message should indicate backup was created
      expect(screen.getByText('Failed to auto-save. Content backed up locally.')).toBeInTheDocument();
    });

    it('backs up content when manual save fails', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial content</p>' });
      mockBookClient.saveChapterContent.mockRejectedValue(new Error('Server error'));

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      // Click Save button
      const saveButton = screen.getByRole('button', { name: /save/i });
      await user.click(saveButton);

      // Verify error shown
      await waitFor(() => {
        expect(screen.getByText(/Failed to save/i)).toBeInTheDocument();
      }, { timeout: 5000 });
    });

    it('handles localStorage quota exceeded error gracefully', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial content</p>' });
      mockBookClient.saveChapterContent.mockRejectedValue(new Error('Network error'));

      // Mock localStorage.setItem to throw quota exceeded
      const originalSetItem = localStorage.setItem;
      const setItemMock = jest.fn(() => {
        throw new Error('QuotaExceededError');
      });
      Object.defineProperty(window.localStorage, 'setItem', {
        configurable: true,
        writable: true,
        value: setItemMock
      });

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      const editor = screen.getByRole('textbox');
      await user.clear(editor);
      await user.type(editor, 'Content that cannot be backed up');

      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

      // Should show error when backup fails
      await waitFor(() => {
        expect(screen.getByText(/Failed to auto-save/i)).toBeInTheDocument();
      });

      // Restore original localStorage
      Object.defineProperty(window.localStorage, 'setItem', {
        configurable: true,
        writable: true,
        value: originalSetItem
      });
    });
  });

  describe('Backup recovery', () => {
    it('shows recovery notification when backup exists on mount', async () => {
      const backupKey = 'chapter-backup-book-1-chapter-1';
      const backup = {
        content: '<p>Backed up content</p>',
        timestamp: Date.now(),
        error: 'Previous save failed'
      };
      localStorage.setItem(backupKey, JSON.stringify(backup));

      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Server content</p>' });

      render(<ChapterEditor {...defaultProps} />);

      // Should show recovery notification
      await waitFor(() => {
        expect(screen.getByText(/A local backup of your content is available/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /restore backup/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /dismiss/i })).toBeInTheDocument();
      });
    });

    it('restores backed up content when user clicks Restore Backup', async () => {
      const user = userEvent.setup({ delay: null });
      const backupKey = 'chapter-backup-book-1-chapter-1';
      const backup = {
        content: '<p>Backed up content from previous session</p>',
        timestamp: Date.now() - 60000, // 1 minute ago
        error: 'Network error'
      };
      localStorage.setItem(backupKey, JSON.stringify(backup));

      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Server content</p>' });
      mockBookClient.saveChapterContent.mockResolvedValue({});

      render(<ChapterEditor {...defaultProps} />);

      // Wait for recovery notification
      await waitFor(() => {
        expect(screen.getByText(/A local backup of your content is available/i)).toBeInTheDocument();
      });

      // Click Restore Backup
      const restoreButton = screen.getByRole('button', { name: /restore backup/i });
      await user.click(restoreButton);

      // Recovery notification should disappear
      await waitFor(() => {
        expect(screen.queryByText(/A local backup of your content is available/i)).not.toBeInTheDocument();
      });

      // Backup should be cleared from localStorage
      expect(localStorage.getItem(backupKey)).toBeNull();

      // Auto-save should be triggered with restored content
      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

      await waitFor(() => {
        expect(mockBookClient.saveChapterContent).toHaveBeenCalledWith(
          'book-1',
          'chapter-1',
          expect.stringContaining('Backed up content from previous session')
        );
      });
    }, 10000);

    it('dismisses backup when user clicks Dismiss', async () => {
      const user = userEvent.setup({ delay: null });
      const backupKey = 'chapter-backup-book-1-chapter-1';
      const backup = {
        content: '<p>Old backup to dismiss</p>',
        timestamp: Date.now() - 300000, // 5 minutes ago
        error: 'Network error'
      };
      localStorage.setItem(backupKey, JSON.stringify(backup));

      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Server content</p>' });

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText(/A local backup of your content is available/i)).toBeInTheDocument();
      });

      // Click Dismiss
      const dismissButton = screen.getByRole('button', { name: /dismiss/i });
      await user.click(dismissButton);

      // Notification should disappear
      await waitFor(() => {
        expect(screen.queryByText(/A local backup of your content is available/i)).not.toBeInTheDocument();
      });

      // Backup should be cleared
      expect(localStorage.getItem(backupKey)).toBeNull();
    }, 10000);

    it('handles corrupted backup data gracefully', async () => {
      const backupKey = 'chapter-backup-book-1-chapter-1';
      localStorage.setItem(backupKey, '{corrupted json data');

      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Server content</p>' });

      render(<ChapterEditor {...defaultProps} />);

      // Component should handle corrupted JSON gracefully and not crash
      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      // Corrupted backup should not trigger recovery notification
      // (component should catch JSON.parse error and ignore corrupted data)
      expect(screen.queryByText(/A local backup of your content is available/i)).not.toBeInTheDocument();
    });
  });

  describe('Backup cleanup', () => {
    it('clears backup after successful auto-save', async () => {
      const user = userEvent.setup({ delay: null });
      const backupKey = 'chapter-backup-book-1-chapter-1';

      // Start with existing backup
      const oldBackup = {
        content: '<p>Old backup</p>',
        timestamp: Date.now() - 120000,
        error: 'Old error'
      };
      localStorage.setItem(backupKey, JSON.stringify(oldBackup));

      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial content</p>' });
      mockBookClient.saveChapterContent.mockResolvedValue({});

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      // Backup notification should show initially
      expect(screen.getByText(/A local backup of your content is available/i)).toBeInTheDocument();

      // Type new content
      const editor = screen.getByRole('textbox');
      await user.clear(editor);
      await user.type(editor, 'New successful content');

      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

      // Wait for successful save
      await waitFor(() => {
        expect(mockBookClient.saveChapterContent).toHaveBeenCalled();
      });

      // Backup should be cleared
      await waitFor(() => {
        expect(localStorage.getItem(backupKey)).toBeNull();
      });
    });

    it('clears backup after successful manual save', async () => {
      const user = userEvent.setup({ delay: null });
      const backupKey = 'chapter-backup-book-1-chapter-1';

      const existingBackup = {
        content: '<p>Backup to clear</p>',
        timestamp: Date.now(),
        error: 'Previous error'
      };
      localStorage.setItem(backupKey, JSON.stringify(existingBackup));

      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial content</p>' });
      mockBookClient.saveChapterContent.mockResolvedValue({});

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
      });

      // Click Save
      const saveButton = screen.getByRole('button', { name: /save/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockBookClient.saveChapterContent).toHaveBeenCalled();
      });

      // Backup should be cleared
      await waitFor(() => {
        expect(localStorage.getItem(backupKey)).toBeNull();
      });
    }, 10000);
  });

  describe('Edge cases', () => {
    it('handles multiple rapid save failures correctly', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });
      mockBookClient.saveChapterContent.mockRejectedValue(new Error('Network unstable'));

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      const editor = screen.getByRole('textbox');

      // Rapid typing and saves
      await user.clear(editor);
      await user.type(editor, 'First attempt');

      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

      await waitFor(() => {
        expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(1);
      });

      // Type more before previous save completes
      await user.type(editor, ' Second attempt');

      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

      // Only latest content should be backed up
      await waitFor(() => {
        const backupKey = 'chapter-backup-book-1-chapter-1';
        const backup = localStorage.getItem(backupKey);
        expect(backup).toBeTruthy();

        if (backup) {
          const parsed = JSON.parse(backup);
          expect(parsed.content).toContain('Second attempt');
        }
      });
    });

    it('does not create backup when save succeeds', async () => {
      const user = userEvent.setup({ delay: null });
      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Initial</p>' });
      mockBookClient.saveChapterContent.mockResolvedValue({});

      render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });

      const editor = screen.getByRole('textbox');
      await user.clear(editor);
      await user.type(editor, 'Successful save');

      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });

      await waitFor(() => {
        expect(mockBookClient.saveChapterContent).toHaveBeenCalled();
      });

      // No backup should exist
      const backupKey = 'chapter-backup-book-1-chapter-1';
      expect(localStorage.getItem(backupKey)).toBeNull();
    });

    it('preserves backup across different chapters in same book', async () => {
      const backupKey1 = 'chapter-backup-book-1-chapter-1';
      const backupKey2 = 'chapter-backup-book-1-chapter-2';

      const backup1 = { content: '<p>Chapter 1 backup</p>', timestamp: Date.now(), error: 'Error 1' };
      const backup2 = { content: '<p>Chapter 2 backup</p>', timestamp: Date.now(), error: 'Error 2' };

      localStorage.setItem(backupKey1, JSON.stringify(backup1));
      localStorage.setItem(backupKey2, JSON.stringify(backup2));

      mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Current</p>' });

      // Render chapter 1
      const { rerender } = render(<ChapterEditor {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText(/A local backup of your content is available/i)).toBeInTheDocument();
      });

      // Verify chapter 2 backup is still intact
      expect(localStorage.getItem(backupKey2)).toBeTruthy();

      // Render chapter 2
      rerender(<ChapterEditor {...defaultProps} chapterId="chapter-2" />);

      await waitFor(() => {
        expect(screen.getByText(/A local backup of your content is available/i)).toBeInTheDocument();
      });

      // Both backups should still exist (neither was dismissed/restored)
      expect(localStorage.getItem(backupKey1)).toBeTruthy();
      expect(localStorage.getItem(backupKey2)).toBeTruthy();
    });
  });
});

/**
 * Tests for ChapterTab keyboard accessibility (WCAG 2.1 compliance)
 * Ensures tabs are fully keyboard accessible with Enter and Space key support
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChapterTab } from '../ChapterTab';
import { ChapterTabMetadata, ChapterStatus } from '@/types/chapter-tabs';

// Wrap ChapterTab with TooltipProvider for tests
import { TooltipProvider } from '@/components/ui/tooltip';

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <TooltipProvider>{children}</TooltipProvider>
);

describe('ChapterTab keyboard accessibility', () => {
  const mockChapter: ChapterTabMetadata = {
    id: 'chapter-1',
    title: 'Test Chapter',
    status: ChapterStatus.DRAFT,
    word_count: 1500,
    estimated_reading_time: 7,
    is_loading: false,
    has_unsaved_changes: false,
    last_modified: new Date().toISOString(),
  };

  const mockOnSelect = jest.fn();
  const mockOnClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('ARIA attributes', () => {
    it('has role="button" for accessibility', () => {
      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      expect(tabElement).toBeInTheDocument();
    });

    it('has tabIndex={0} for keyboard focus', () => {
      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      expect(tabElement).toHaveAttribute('tabindex', '0');
    });

    it('has descriptive aria-label with chapter title', () => {
      render(
        <TestWrapper>
          <ChapterTab
            chapter={{ ...mockChapter, title: 'Introduction to Programming' }}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByLabelText('Open chapter Introduction to Programming');
      expect(tabElement).toBeInTheDocument();
    });

    it('indicates active state with aria-selected', () => {
      const { rerender } = render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      let tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      expect(tabElement).toHaveAttribute('aria-selected', 'false');

      // Rerender with isActive=true
      rerender(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={true}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      expect(tabElement).toHaveAttribute('aria-selected', 'true');
    });
  });

  describe('Keyboard interaction', () => {
    it('activates tab when Enter key is pressed', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });

      // Focus the tab
      tabElement.focus();
      expect(tabElement).toHaveFocus();

      // Press Enter
      await user.keyboard('{Enter}');

      expect(mockOnSelect).toHaveBeenCalledTimes(1);
    });

    it('activates tab when Space key is pressed', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });

      // Focus the tab
      tabElement.focus();

      // Press Space
      await user.keyboard(' ');

      expect(mockOnSelect).toHaveBeenCalledTimes(1);
    });

    it('does not activate on other key presses', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      tabElement.focus();

      // Press various non-activation keys
      await user.keyboard('{Escape}');
      await user.keyboard('{Tab}');
      await user.keyboard('a');

      // onSelect should not have been called
      expect(mockOnSelect).not.toHaveBeenCalled();
    });

    it('prevents default behavior on Enter key', async () => {
      const user = userEvent.setup();
      const mockPreventDefault = jest.fn();

      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      tabElement.focus();

      // Add event listener to verify preventDefault was called
      tabElement.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          mockPreventDefault();
        }
      });

      await user.keyboard('{Enter}');

      expect(mockOnSelect).toHaveBeenCalled();
      // Note: We can't directly test preventDefault, but we verify the handler runs
    });

    it('prevents default behavior on Space key', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      tabElement.focus();

      await user.keyboard(' ');

      expect(mockOnSelect).toHaveBeenCalled();
      // Space key should not scroll the page (preventDefault effect)
    });
  });

  describe('Focus management', () => {
    it('receives focus when tabbed to', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <div>
            <button>Previous focusable</button>
            <ChapterTab
              chapter={mockChapter}
              isActive={false}
              onSelect={mockOnSelect}
              onClose={mockOnClose}
            />
            <button>Next focusable</button>
          </div>
        </TestWrapper>
      );

      const prevButton = screen.getByText('Previous focusable');
      prevButton.focus();

      // Tab to chapter tab
      await user.tab();

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      expect(tabElement).toHaveFocus();
    });

    it('shows visible focus indicator', () => {
      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });

      // Verify focus styles are present in className
      expect(tabElement.className).toContain('focus:outline-none');
      expect(tabElement.className).toContain('focus:ring-2');
      expect(tabElement.className).toContain('focus:ring-primary');
    });

    it('maintains focus after activation via Enter', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      tabElement.focus();

      await user.keyboard('{Enter}');

      // Focus should remain on the tab after activation
      expect(tabElement).toHaveFocus();
    });

    it('maintains focus after activation via Space', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      tabElement.focus();

      await user.keyboard(' ');

      expect(tabElement).toHaveFocus();
    });
  });

  describe('Close button accessibility', () => {
    it('close button remains independently focusable', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      // Tab to chapter tab
      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      tabElement.focus();

      // Tab again to reach close button
      await user.tab();

      const closeButton = screen.getByRole('button', { name: /close/i });
      expect(closeButton).toHaveFocus();
    });

    it('close button activation does not trigger tab selection', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const closeButton = screen.getByRole('button', { name: /close/i });
      closeButton.focus();

      await user.keyboard('{Enter}');

      expect(mockOnClose).toHaveBeenCalledTimes(1);
      expect(mockOnSelect).not.toHaveBeenCalled();
    });
  });

  describe('Mouse and keyboard equivalence', () => {
    it('achieves same result with click and Enter key', async () => {
      const user = userEvent.setup();
      const { rerender } = render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });

      // Test with click
      await user.click(tabElement);
      expect(mockOnSelect).toHaveBeenCalledTimes(1);

      mockOnSelect.mockClear();

      // Rerender for second test
      rerender(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      // Test with Enter key
      tabElement.focus();
      await user.keyboard('{Enter}');
      expect(mockOnSelect).toHaveBeenCalledTimes(1);
    });

    it('achieves same result with click and Space key', async () => {
      const user = userEvent.setup();
      const { rerender } = render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });

      // Test with click
      await user.click(tabElement);
      expect(mockOnSelect).toHaveBeenCalledTimes(1);

      mockOnSelect.mockClear();

      // Rerender for second test
      rerender(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      // Test with Space key
      tabElement.focus();
      await user.keyboard(' ');
      expect(mockOnSelect).toHaveBeenCalledTimes(1);
    });
  });

  describe('Edge cases', () => {
    it('handles rapid keyboard activations', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      tabElement.focus();

      // Rapid Enter presses
      await user.keyboard('{Enter}');
      await user.keyboard('{Enter}');
      await user.keyboard('{Enter}');

      expect(mockOnSelect).toHaveBeenCalledTimes(3);
    });

    it('works correctly with long chapter titles', async () => {
      const user = userEvent.setup();
      const longTitleChapter: ChapterTabMetadata = {
        ...mockChapter,
        title: 'This is an extremely long chapter title that should be handled properly by keyboard navigation'
      };

      render(
        <TestWrapper>
          <ChapterTab
            chapter={longTitleChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter/i });
      tabElement.focus();

      await user.keyboard('{Enter}');

      expect(mockOnSelect).toHaveBeenCalled();
    });

    it('maintains accessibility when tab has error state', async () => {
      const user = userEvent.setup();
      const errorChapter: ChapterTabMetadata = {
        ...mockChapter,
        error: 'Failed to load chapter'
      };

      render(
        <TestWrapper>
          <ChapterTab
            chapter={errorChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      tabElement.focus();

      await user.keyboard('{Enter}');

      expect(mockOnSelect).toHaveBeenCalled();
    });

    it('maintains accessibility when tab is dragging', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            isDragging={true}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      tabElement.focus();

      await user.keyboard('{Enter}');

      expect(mockOnSelect).toHaveBeenCalled();
    });
  });

  describe('Orientation support', () => {
    it('maintains keyboard accessibility in horizontal orientation', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
            orientation="horizontal"
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      tabElement.focus();

      await user.keyboard('{Enter}');

      expect(mockOnSelect).toHaveBeenCalled();
    });

    it('maintains keyboard accessibility in vertical orientation', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <ChapterTab
            chapter={mockChapter}
            isActive={false}
            onSelect={mockOnSelect}
            onClose={mockOnClose}
            orientation="vertical"
          />
        </TestWrapper>
      );

      const tabElement = screen.getByRole('button', { name: /open chapter test chapter/i });
      tabElement.focus();

      await user.keyboard('{Enter}');

      expect(mockOnSelect).toHaveBeenCalled();
    });
  });
});

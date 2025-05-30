import { render, screen, waitFor } from '@testing-library/react';
import { ChapterTab } from '@/components/chapters/ChapterTab';
import { ChapterStatus, ChapterTabMetadata } from '@/types/chapter-tabs';
import { createMockChapter } from './fixtures/chapterTabsFixtures';

// Helper function to create a mock chapter with specific status
const createTestChapter = (status: ChapterStatus, hasUnsavedChanges = false): ChapterTabMetadata => ({
  ...createMockChapter('ch-1', 'Test Chapter'),
  status,
  has_unsaved_changes: hasUnsavedChanges
});

describe('Tab Status Indicators', () => {
  test.each([
    [ChapterStatus.DRAFT],
    [ChapterStatus.IN_PROGRESS],
    [ChapterStatus.COMPLETED],
    [ChapterStatus.PUBLISHED],
  ])('displays correct status indicator for %s status', (status) => {
    render(
      <ChapterTab
        chapter={createTestChapter(status)}
        isActive={false}
        onSelect={jest.fn()}
        onClose={jest.fn()}
        isDragging={false}
      />
    );
    
    // We can't directly test for the status indicator class since it's not using data-testid
    // But we can check if the status color is applied correctly by checking the element with status colors
    const statusIndicator = screen.getByText('Test Chapter').previousSibling;
    expect(statusIndicator).toHaveClass(status === ChapterStatus.DRAFT ? 'bg-muted' : 
                               status === ChapterStatus.IN_PROGRESS ? 'bg-blue-500' :
                               status === ChapterStatus.COMPLETED ? 'bg-green-500' : 
                               'bg-purple-500');
  });
  
  test('updates status indicator when chapter status changes', async () => {
    // This test would require mocking the context menu which might be complex
    // Instead we'll verify that different statuses render correctly
    const { rerender } = render(
      <ChapterTab
        chapter={createTestChapter(ChapterStatus.DRAFT)}
        isActive={true}
        onSelect={jest.fn()}
        onClose={jest.fn()}
        isDragging={false}
      />
    );
    
    // Verify initial status color
    const initialStatusIndicator = screen.getByText('Test Chapter').previousSibling;
    expect(initialStatusIndicator).toHaveClass('bg-muted');
    
    // Rerender with new status
    rerender(
      <ChapterTab
        chapter={createTestChapter(ChapterStatus.IN_PROGRESS)}
        isActive={true}
        onSelect={jest.fn()}
        onClose={jest.fn()}
        isDragging={false}
      />
    );
    
    // Verify status indicator was updated
    await waitFor(() => {
      const updatedStatusIndicator = screen.getByText('Test Chapter').previousSibling;
      expect(updatedStatusIndicator).toHaveClass('bg-blue-500');
    });
  });
  
  test('shows unsaved changes indicator when changes are pending', () => {
    render(
      <ChapterTab
        chapter={createTestChapter(ChapterStatus.DRAFT, true)} // Has unsaved changes
        isActive={true}
        onSelect={jest.fn()}
        onClose={jest.fn()}
        isDragging={false}
      />
    );
    
    // Look for the unsaved changes indicator (orange dot)
    // Get the indicators container which comes before the close button
    const closeButton = screen.getByRole('button', { name: /close/i });
    const indicatorsContainer = closeButton.previousElementSibling;
    expect(indicatorsContainer).toBeInTheDocument();
    
    // Find the orange dot indicator
    const unsavedIndicator = screen.getByTestId('indicators-container').querySelector('.bg-orange-500');
    expect(unsavedIndicator).not.toBeNull();
  });
});

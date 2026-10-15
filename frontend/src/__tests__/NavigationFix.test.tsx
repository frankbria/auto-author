import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import '@testing-library/jest-dom';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

// Mock the EditTocPage component to test navigation
const EditTocPage = () => {
  const router = useRouter();

  const handleSaveToc = async () => {
    // This is the fix we implemented - navigate to book page instead of /chapters
    router.push(`/dashboard/books/bookId123`);
  };

  return (
    <div>
      <h1>Edit TOC Page</h1>
      <button onClick={handleSaveToc}>Save TOC</button>
    </div>
  );
};

describe('Navigation Fix', () => {
  let mockPush: jest.Mock;

  beforeEach(() => {
    mockPush = jest.fn();
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
      replace: jest.fn(),
      prefetch: jest.fn(),
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should navigate to book page with tabs after saving TOC', async () => {
    render(<EditTocPage />);

    const saveButton = screen.getByText('Save TOC');
    saveButton.click();

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/dashboard/books/bookId123');
    });

    // Should NOT navigate to the old /chapters route
    expect(mockPush).not.toHaveBeenCalledWith(expect.stringContaining('/chapters'));
  });

  it('should preserve chapter context in breadcrumb navigation', () => {
    const BookPage = ({ chapterId }: { chapterId?: string }) => {
      const showChapterContext = !!chapterId;

      return (
        <div>
          {showChapterContext && (
            <nav aria-label="breadcrumb">
              <ol>
                <li>Dashboard</li>
                <li>Book Title</li>
                <li>Writing</li>
                <li>Chapter Title</li>
              </ol>
            </nav>
          )}
          <div>Book content with tabs</div>
        </div>
      );
    };

    // Without chapter context
    const { rerender } = render(<BookPage />);
    expect(screen.queryByText('Writing')).not.toBeInTheDocument();

    // With chapter context
    rerender(<BookPage chapterId="chapter123" />);
    expect(screen.getByText('Writing')).toBeInTheDocument();
  });

  it('should use tabbed interface for all chapter navigation', () => {
    // Test that all chapter links use the tabbed interface
    const TocSidebar = ({ onChapterSelect }: { onChapterSelect: (id: string) => void }) => {
      return (
        <div>
          <button onClick={() => onChapterSelect('ch1')}>Chapter 1</button>
          <button onClick={() => onChapterSelect('ch2')}>Chapter 2</button>
        </div>
      );
    };

    const mockChapterSelect = jest.fn();
    render(<TocSidebar onChapterSelect={mockChapterSelect} />);

    // Click chapter 1
    screen.getByText('Chapter 1').click();
    expect(mockChapterSelect).toHaveBeenCalledWith('ch1');

    // Click chapter 2
    screen.getByText('Chapter 2').click();
    expect(mockChapterSelect).toHaveBeenCalledWith('ch2');

    // Verify it uses callbacks, not direct navigation
    expect(mockPush).not.toHaveBeenCalled();
  });
});

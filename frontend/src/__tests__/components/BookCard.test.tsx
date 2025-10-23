import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import BookCard, { BookProject } from '@/components/BookCard';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

// Mock the UI components to avoid issues with imports
jest.mock('@/components/ui/card', () => ({
  Card: ({ children, className, onClick }: any) => (
    <div className={className} onClick={onClick} role="article">{children}</div>
  ),
  CardContent: ({ children }: any) => <div>{children}</div>,
  CardFooter: ({ children, className }: any) => <div className={className}>{children}</div>,
  CardTitle: ({ children, className, title }: any) => <h3 className={className} title={title}>{children}</h3>,
}));

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, className, disabled, size }: any) => (
    <button 
      onClick={onClick} 
      className={className} 
      disabled={disabled}
      data-size={size}
    >
      {children}
    </button>
  ),
}));

jest.mock('@/components/ui/alert-dialog', () => ({
  AlertDialog: ({ children, open, onOpenChange }: any) => (
    <div data-testid="alert-dialog-wrapper">
      {open && (
        <div data-testid="alert-dialog" role="dialog">
          {typeof children === 'function' ? children({ open, onOpenChange }) : children}
        </div>
      )}
    </div>
  ),
  AlertDialogContent: ({ children }: any) => <div data-testid="alert-content">{children}</div>,
  AlertDialogHeader: ({ children }: any) => <div>{children}</div>,
  AlertDialogTitle: ({ children }: any) => <h2>{children}</h2>,
  AlertDialogDescription: ({ children }: any) => <p>{children}</p>,
  AlertDialogFooter: ({ children }: any) => <div>{children}</div>,
  AlertDialogAction: ({ children, onClick, disabled, className }: any) => (
    <button onClick={onClick} disabled={disabled} className={className} data-testid="alert-action">
      {children}
    </button>
  ),
  AlertDialogCancel: ({ children, onClick, disabled }: any) => (
    <button onClick={onClick || (() => {})} disabled={disabled} data-testid="alert-cancel">
      {children}
    </button>
  ),
}));

jest.mock('lucide-react', () => ({
  Trash2: ({ className }: any) => <span className={className} data-testid="trash-icon">Trash</span>,
}));

// Mock DeleteBookModal
jest.mock('@/components/books', () => ({
  DeleteBookModal: ({ isOpen, bookTitle, onConfirm, isDeleting, onOpenChange }: any) => (
    isOpen ? (
      <div data-testid="delete-book-modal" role="dialog">
        <h2>Delete Book</h2>
        <p>Are you sure you want to delete &quot;{bookTitle}&quot;?</p>
        <p>All chapters and content will be permanently deleted</p>
        <button onClick={() => onOpenChange(false)} data-testid="modal-cancel">Cancel</button>
        <button onClick={onConfirm} disabled={isDeleting} data-testid="modal-confirm">
          {isDeleting ? 'Deleting...' : 'Delete'}
        </button>
      </div>
    ) : null
  ),
}));

describe('BookCard', () => {
  const mockPush = jest.fn();
  
  const mockBook: BookProject = {
    id: 'book-123',
    title: 'Test Book Title',
    description: 'This is a test book description',
    subtitle: 'Test Subtitle',
    genre: 'Fiction',
    target_audience: 'Young Adults',
    cover_image_url: 'https://example.com/cover.jpg',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
    published: false,
    collaborators: [],
    owner_id: 'user-123',
    chapters: 5,
    progress: 75,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
    });
  });

  it('should render book information correctly', () => {
    render(<BookCard book={mockBook} />);
    
    expect(screen.getByText('Test Book Title')).toBeInTheDocument();
    expect(screen.getByText('This is a test book description')).toBeInTheDocument();
    expect(screen.getByText('5 chapters')).toBeInTheDocument();
    expect(screen.getByText('Progress')).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('should format date correctly', () => {
    render(<BookCard book={mockBook} />);

    // Check for the date part - text may have whitespace/newlines
    expect(screen.getByText(/Jan 15, 2024/)).toBeInTheDocument();
    expect(screen.getByText(/Last edited/)).toBeInTheDocument();
  });

  it('should show "New" badge when book has no chapters', () => {
    const newBook = { ...mockBook, chapters: 0 };
    render(<BookCard book={newBook} />);
    
    expect(screen.getByText('New')).toBeInTheDocument();
    expect(screen.getByText('Ready to start writing! Click below to begin creating your book content.')).toBeInTheDocument();
  });

  it('should navigate to book page when card is clicked', () => {
    render(<BookCard book={mockBook} />);
    
    const card = screen.getByRole('article');
    fireEvent.click(card);
    
    expect(mockPush).toHaveBeenCalledWith('/dashboard/books/book-123');
  });

  it('should navigate to book page when Open Project button is clicked', () => {
    render(<BookCard book={mockBook} />);
    
    const openButton = screen.getByText('Open Project');
    fireEvent.click(openButton);
    
    expect(mockPush).toHaveBeenCalledWith('/dashboard/books/book-123');
  });

  it('should call custom onClick handler when provided', () => {
    const mockOnClick = jest.fn();
    render(<BookCard book={mockBook} onClick={mockOnClick} />);
    
    const card = screen.getByRole('article');
    fireEvent.click(card);
    
    expect(mockOnClick).toHaveBeenCalled();
    expect(mockPush).not.toHaveBeenCalled();
  });

  describe('Delete functionality', () => {
    const mockOnDelete = jest.fn();

    it('should show delete button when onDelete prop is provided', () => {
      render(<BookCard book={mockBook} onDelete={mockOnDelete} />);
      
      const deleteButton = screen.getByTestId('trash-icon');
      expect(deleteButton).toBeInTheDocument();
    });

    it('should not show delete button when onDelete prop is not provided', () => {
      render(<BookCard book={mockBook} />);
      
      const deleteButton = screen.queryByTestId('trash-icon');
      expect(deleteButton).not.toBeInTheDocument();
    });

    it('should show confirmation dialog when delete button is clicked', () => {
      render(<BookCard book={mockBook} onDelete={mockOnDelete} />);
      
      const deleteButton = screen.getByTestId('trash-icon').closest('button')!;
      fireEvent.click(deleteButton);
      
      expect(screen.getByText('Delete Book')).toBeInTheDocument();
      expect(screen.getByText(/Are you sure you want to delete "Test Book Title"\?/)).toBeInTheDocument();
      expect(screen.getByText(/All chapters and content will be permanently deleted/)).toBeInTheDocument();
    });

    it('should close dialog when cancel is clicked', async () => {
      render(<BookCard book={mockBook} onDelete={mockOnDelete} />);

      const deleteButton = screen.getByTestId('trash-icon').closest('button')!;
      fireEvent.click(deleteButton);

      expect(screen.getByTestId('delete-book-modal')).toBeInTheDocument();

      const cancelButton = screen.getByTestId('modal-cancel');
      fireEvent.click(cancelButton);

      // Dialog should be closed
      await waitFor(() => {
        expect(screen.queryByTestId('delete-book-modal')).not.toBeInTheDocument();
      });

      expect(mockOnDelete).not.toHaveBeenCalled();
    });

    it('should call onDelete when delete is confirmed', async () => {
      mockOnDelete.mockResolvedValue(undefined);
      render(<BookCard book={mockBook} onDelete={mockOnDelete} />);

      const deleteButton = screen.getByTestId('trash-icon').closest('button')!;
      fireEvent.click(deleteButton);

      const confirmButton = screen.getByTestId('modal-confirm');
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(mockOnDelete).toHaveBeenCalledWith('book-123');
      });
    });

    it('should show loading state during deletion', async () => {
      mockOnDelete.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
      render(<BookCard book={mockBook} onDelete={mockOnDelete} />);

      const deleteButton = screen.getByTestId('trash-icon').closest('button')!;
      fireEvent.click(deleteButton);

      const confirmButton = screen.getByTestId('modal-confirm');
      fireEvent.click(confirmButton);

      expect(screen.getByText('Deleting...')).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.queryByText('Deleting...')).not.toBeInTheDocument();
      });
    });

    it('should handle deletion errors gracefully', async () => {
      const consoleError = jest.spyOn(console, 'error').mockImplementation();
      mockOnDelete.mockRejectedValue(new Error('Delete failed'));

      render(<BookCard book={mockBook} onDelete={mockOnDelete} />);

      const deleteButton = screen.getByTestId('trash-icon').closest('button')!;
      fireEvent.click(deleteButton);

      const confirmButton = screen.getByTestId('modal-confirm');
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(consoleError).toHaveBeenCalledWith('Failed to delete book:', expect.any(Error));
      });

      consoleError.mockRestore();
    });

    it('should prevent card navigation when delete button is clicked', () => {
      render(<BookCard book={mockBook} onDelete={mockOnDelete} />);
      
      const deleteButton = screen.getByTestId('trash-icon').closest('button')!;
      fireEvent.click(deleteButton);
      
      expect(mockPush).not.toHaveBeenCalled();
    });
  });

  it('should truncate long titles and descriptions', () => {
    const longBook = {
      ...mockBook,
      title: 'This is a very long book title that should be truncated in the UI',
      description: 'This is an extremely long description that goes on and on and should definitely be truncated in the card view to maintain a clean layout',
    };
    
    render(<BookCard book={longBook} />);
    
    const title = screen.getByText(longBook.title);
    const description = screen.getByText(longBook.description);
    
    expect(title).toHaveClass('truncate');
    expect(description).toHaveClass('line-clamp-2');
  });

  it('should handle missing optional fields gracefully', () => {
    const minimalBook: BookProject = {
      id: 'book-456',
      title: 'Minimal Book',
      chapters: 0,
      progress: 0,
    };
    
    render(<BookCard book={minimalBook} />);
    
    expect(screen.getByText('Minimal Book')).toBeInTheDocument();
    expect(screen.queryByText(/Last edited/)).toBeInTheDocument();
  });
});
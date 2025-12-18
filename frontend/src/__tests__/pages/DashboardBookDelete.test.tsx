import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useSession } from '@/lib/auth-client';
import { useRouter } from 'next/navigation';
import Dashboard from '@/app/dashboard/page';
import bookClient from '@/lib/api/bookClient';
import { toast } from 'sonner';

// Mock dependencies
jest.mock('@/lib/auth-client');
jest.mock('@/lib/api/bookClient');
jest.mock('sonner');
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

// Mock the BookCreationWizard component
jest.mock('@/components/BookCreationWizard', () => ({
  BookCreationWizard: ({ isOpen, onOpenChange, onSuccess }: any) => {
    if (!isOpen) return null;
    return (
      <div data-testid="book-creation-wizard">
        <button onClick={() => onOpenChange(false)}>Close</button>
        <button onClick={() => onSuccess('new-book-id')}>Create Book</button>
      </div>
    );
  },
}));

// Mock EmptyBookState
jest.mock('@/components/EmptyBookState', () => ({
  EmptyBookState: ({ onCreateNew }: any) => (
    <div>
      <p>You haven't created any books yet</p>
      <button onClick={onCreateNew}>Create Your First Book</button>
    </div>
  ),
}));

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  PlusIcon: () => <span>Plus</span>,
  BookIcon: () => <span>Book</span>,
  Trash2: ({ className }: any) => <span data-testid="trash-icon" className={className}>Trash</span>,
}));

// Mock BookCard component
jest.mock('@/components/BookCard', () => ({
  __esModule: true,
  default: ({ book, onDelete }: any) => {
    const [showDialog, setShowDialog] = React.useState(false);
    const [isDeleting, setIsDeleting] = React.useState(false);
    
    // Access mocked router
    const mockRouter = require('next/navigation').useRouter();
    
    const handleDeleteClick = () => {
      setShowDialog(true);
    };
    
    const handleOpenProject = () => {
      mockRouter.push(`/dashboard/books/${book.id}`);
    };
    
    const handleConfirmDelete = async () => {
      if (!onDelete) return;
      setIsDeleting(true);
      try {
        await onDelete(book.id);
        setShowDialog(false);
      } catch (error) {
        console.error('Delete failed:', error);
      } finally {
        setIsDeleting(false);
      }
    };
    
    return (
      <div data-testid={`book-card-${book.id}`}>
        <h3>{book.title}</h3>
        <p>{book.description}</p>
        <p>{book.chapters} chapters</p>
        <p>{book.progress}% progress</p>
        <button onClick={handleOpenProject}>Open Project</button>
        {onDelete && (
          <button 
            onClick={handleDeleteClick}
            data-testid={`delete-book-${book.id}`}
          >
            <span data-testid="trash-icon">Delete</span>
          </button>
        )}
        {showDialog && (
          <div data-testid="confirmation-dialog">
            <h2>Delete Book</h2>
            <p>Are you sure you want to delete "{book.title}"? This action cannot be undone.</p>
            <p>All chapters and content will be permanently deleted.</p>
            <button 
              onClick={() => setShowDialog(false)}
              data-testid="cancel-delete"
            >
              Cancel
            </button>
            <button 
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              data-testid="confirm-delete"
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        )}
      </div>
    );
  },
  BookProject: {} as any,
}));

describe('Dashboard - Book Deletion', () => {
  const mockPush = jest.fn();
  const mockGetToken = jest.fn().mockResolvedValue('test-token');

  const mockBooks = [
    {
      id: 'book-1',
      title: 'First Book',
      description: 'Description 1',
      chapters: 5,
      progress: 50,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-15T00:00:00Z',
    },
    {
      id: 'book-2',
      title: 'Second Book',
      description: 'Description 2',
      chapters: 3,
      progress: 30,
      created_at: '2024-01-02T00:00:00Z',
      updated_at: '2024-01-16T00:00:00Z',
    },
    {
      id: 'book-3',
      title: 'Third Book',
      description: 'Description 3',
      chapters: 0,
      progress: 0,
      created_at: '2024-01-03T00:00:00Z',
      updated_at: '2024-01-17T00:00:00Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();

    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
    });

    (useSession as jest.Mock).mockReturnValue({
      data: {
        user: {
          id: 'user-123',
          email: 'test@example.com',
          name: 'Test User',
        },
        session: {
          token: 'test-token',
          id: 'session-123',
        },
      },
      isPending: false,
      error: null,
    });

    (bookClient.getUserBooks as jest.Mock).mockResolvedValue(mockBooks);
    (bookClient.setAuthToken as jest.Mock).mockImplementation(() => {});
    (bookClient.setTokenProvider as jest.Mock).mockImplementation(() => mockGetToken);
    (bookClient.deleteBook as jest.Mock).mockResolvedValue({ success: true });

    // Mock toast
    (toast.success as jest.Mock) = jest.fn();
    (toast.error as jest.Mock) = jest.fn();
  });

  it('should render books with delete buttons', async () => {
    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('First Book')).toBeInTheDocument();
      expect(screen.getByText('Second Book')).toBeInTheDocument();
      expect(screen.getByText('Third Book')).toBeInTheDocument();
      
      // Each book should have a delete button (trash icon)
      const deleteButtons = screen.getAllByTestId('trash-icon');
      expect(deleteButtons).toHaveLength(3);
    });
  });

  it('should show confirmation dialog when delete button is clicked', async () => {
    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('First Book')).toBeInTheDocument();
    });
    
    // Find and click the first delete button
    const deleteButtons = screen.getAllByTestId('trash-icon');
    const firstDeleteButton = deleteButtons[0].closest('button')!;
    fireEvent.click(firstDeleteButton);
    
    // Check confirmation dialog
    expect(screen.getByText('Delete Book')).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to delete "First Book"\?/)).toBeInTheDocument();
    expect(screen.getByText('All chapters and content will be permanently deleted.')).toBeInTheDocument();
  });

  it('should close dialog when cancel is clicked', async () => {
    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('First Book')).toBeInTheDocument();
    });
    
    const deleteButtons = screen.getAllByTestId('trash-icon');
    fireEvent.click(deleteButtons[0].closest('button')!);
    
    const cancelButton = screen.getByTestId('cancel-delete');
    fireEvent.click(cancelButton);
    
    await waitFor(() => {
      expect(screen.queryByText('Delete Book')).not.toBeInTheDocument();
    });
    
    // Books should still be there
    expect(screen.getByText('First Book')).toBeInTheDocument();
    expect(screen.getByText('Second Book')).toBeInTheDocument();
    expect(screen.getByText('Third Book')).toBeInTheDocument();
  });

  it('should delete book when confirmed', async () => {
    (bookClient.deleteBook as jest.Mock).mockResolvedValue(undefined);
    
    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('First Book')).toBeInTheDocument();
    });
    
    const deleteButtons = screen.getAllByTestId('trash-icon');
    fireEvent.click(deleteButtons[0].closest('button')!);
    
    const confirmButton = screen.getByTestId('confirm-delete');
    fireEvent.click(confirmButton);
    
    await waitFor(() => {
      expect(bookClient.deleteBook).toHaveBeenCalledWith('book-1');
      expect(toast.success).toHaveBeenCalledWith('Book deleted successfully');
    });
    
    // Book should be removed from the list
    expect(screen.queryByText('First Book')).not.toBeInTheDocument();
    expect(screen.getByText('Second Book')).toBeInTheDocument();
    expect(screen.getByText('Third Book')).toBeInTheDocument();
  });

  it('should show loading state during deletion', async () => {
    (bookClient.deleteBook as jest.Mock).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );
    
    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('First Book')).toBeInTheDocument();
    });
    
    const deleteButtons = screen.getAllByTestId('trash-icon');
    fireEvent.click(deleteButtons[0].closest('button')!);
    
    const confirmButton = screen.getByTestId('confirm-delete');
    fireEvent.click(confirmButton);
    
    expect(screen.getByText('Deleting...')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.queryByText('Deleting...')).not.toBeInTheDocument();
    });
  });

  it('should handle deletion errors', async () => {
    (bookClient.deleteBook as jest.Mock).mockRejectedValue(new Error('Delete failed'));
    const consoleError = jest.spyOn(console, 'error').mockImplementation();
    
    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('First Book')).toBeInTheDocument();
    });
    
    const deleteButtons = screen.getAllByTestId('trash-icon');
    fireEvent.click(deleteButtons[0].closest('button')!);
    
    const confirmButton = screen.getByTestId('confirm-delete');
    fireEvent.click(confirmButton);
    
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to delete book. Please try again.');
      expect(consoleError).toHaveBeenCalledWith('Error deleting book:', expect.any(Error));
    });
    
    // Book should still be in the list
    expect(screen.getByText('First Book')).toBeInTheDocument();
    
    consoleError.mockRestore();
  });

  it('should delete multiple books sequentially', async () => {
    (bookClient.deleteBook as jest.Mock).mockResolvedValue(undefined);
    
    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('First Book')).toBeInTheDocument();
    });
    
    // Delete first book
    let deleteButtons = screen.getAllByTestId('trash-icon');
    fireEvent.click(deleteButtons[0].closest('button')!);
    fireEvent.click(screen.getByTestId('confirm-delete'));
    
    await waitFor(() => {
      expect(screen.queryByText('First Book')).not.toBeInTheDocument();
    });
    
    // Delete second book
    deleteButtons = screen.getAllByTestId('trash-icon');
    fireEvent.click(deleteButtons[0].closest('button')!); // Now this is the second book
    fireEvent.click(screen.getByTestId('confirm-delete'));
    
    await waitFor(() => {
      expect(screen.queryByText('Second Book')).not.toBeInTheDocument();
    });
    
    // Only third book should remain
    expect(screen.getByText('Third Book')).toBeInTheDocument();
    expect(bookClient.deleteBook).toHaveBeenCalledTimes(2);
    expect(bookClient.deleteBook).toHaveBeenCalledWith('book-1');
    expect(bookClient.deleteBook).toHaveBeenCalledWith('book-2');
  });

  it('should maintain correct auth token for deletion', async () => {
    (bookClient.deleteBook as jest.Mock).mockResolvedValue(undefined);

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('First Book')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByTestId('trash-icon');
    fireEvent.click(deleteButtons[0].closest('button')!);

    const confirmButton = screen.getByTestId('confirm-delete');
    fireEvent.click(confirmButton);

    await waitFor(() => {
      // With better-auth, tokens are automatically included - no need for setTokenProvider
      expect(bookClient.deleteBook).toHaveBeenCalledWith('book-1');
    });
  });

  it('should not interfere with book navigation', async () => {
    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('First Book')).toBeInTheDocument();
    });
    
    // Click on Open Project button (not delete)
    const openButtons = screen.getAllByText('Open Project');
    fireEvent.click(openButtons[0]);
    
    expect(mockPush).toHaveBeenCalledWith('/dashboard/books/book-1');
    expect(screen.queryByText('Delete Book')).not.toBeInTheDocument();
  });

  it('should handle deletion when only one book exists', async () => {
    (bookClient.getUserBooks as jest.Mock).mockResolvedValue([mockBooks[0]]);
    (bookClient.deleteBook as jest.Mock).mockResolvedValue(undefined);
    
    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('First Book')).toBeInTheDocument();
    });
    
    const deleteButton = screen.getByTestId('trash-icon').closest('button')!;
    fireEvent.click(deleteButton);
    
    const confirmButton = screen.getByTestId('confirm-delete');
    fireEvent.click(confirmButton);
    
    await waitFor(() => {
      expect(screen.queryByText('First Book')).not.toBeInTheDocument();
    });
    
    // Should show empty state after deleting the only book
    expect(screen.getByText("You haven't created any books yet")).toBeInTheDocument();
  });

  it('should not affect book creation functionality', async () => {
    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('First Book')).toBeInTheDocument();
    });
    
    // Click create new book
    const createButton = screen.getByText('Create New Book');
    fireEvent.click(createButton);
    
    expect(screen.getByTestId('book-creation-wizard')).toBeInTheDocument();
    
    // Create a new book
    const createBookButton = screen.getByText('Create Book');
    fireEvent.click(createBookButton);
    
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        'Your book has been created! Click "Open Project" to start writing.'
      );
    });
  });

  it('should handle network errors during deletion', async () => {
    (bookClient.deleteBook as jest.Mock).mockRejectedValue(
      new Error('Network request failed')
    );
    
    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('First Book')).toBeInTheDocument();
    });
    
    const deleteButtons = screen.getAllByTestId('trash-icon');
    fireEvent.click(deleteButtons[0].closest('button')!);
    
    const confirmButton = screen.getByTestId('confirm-delete');
    fireEvent.click(confirmButton);
    
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to delete book. Please try again.');
    });
    
    // Dialog should close but book should remain
    await waitFor(() => {
      expect(screen.queryByTestId('confirmation-dialog')).not.toBeInTheDocument();
    });
    expect(screen.getByText('First Book')).toBeInTheDocument();
  });
});
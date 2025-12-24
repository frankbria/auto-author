'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { useSession } from '@/lib/auth-client';
import { Button } from '@/components/ui/button';
import { HugeiconsIcon } from '@hugeicons/react';
import { Add01Icon, Book02Icon } from '@hugeicons/core-free-icons';
import BookCard, { BookProject } from '@/components/BookCard';
import { BookCreationWizard } from '@/components/BookCreationWizard';
import { EmptyBookState } from '@/components/EmptyBookState';
import bookClient from '@/lib/api/bookClient';

export default function Dashboard() {
  const router = useRouter();
  const { data: session, isPending: isSessionPending } = useSession();
  const [projects, setProjects] = useState<BookProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isBookDialogOpen, setIsBookDialogOpen] = useState(false);

  // E2E test mode detection
  const isE2EMode = process.env.NEXT_PUBLIC_BYPASS_AUTH === 'true';

  const fetchBooks = useCallback(async () => {
    // In E2E mode, bypass session user check
    if (!isE2EMode && (!session)) return;

    setIsLoading(true);
    try {
      // Set up token provider for authenticated requests
      const tokenProvider = async () => session?.session.token || null;
      bookClient.setTokenProvider(tokenProvider);

      const books = await bookClient.getUserBooks();
      setProjects(books);
      setError(null);
    } catch (err) {
      console.error('Error fetching books:', err);

      // Check if this is a 404 error (user has no books yet or doesn't exist in DB)
      const is404 = err instanceof Error && (
        err.message.includes('404') ||
        err.message.includes('Not Found') ||
        err.message.includes('not found')
      );

      // In E2E mode, treat empty list as success (no auth token = no books)
      // For 404 errors, treat as empty state (user has no books yet)
      if (isE2EMode || is404) {
        setProjects([]);
        setError(null);
      } else {
        setError('Failed to load your books. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [session, isE2EMode]);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  const handleCreateNewBook = () => {
    setIsBookDialogOpen(true);
  };
  
  const handleBookCreated = (bookId: string) => {
    toast.success('Your book has been created! Click "Open Project" to start writing.');
    fetchBooks();  // Refresh the list of books
    
    // Redirect after a short delay to allow the user to see the success toast
    setTimeout(() => {
      router.push(`/dashboard/books/${bookId}`);
    }, 1500);
  };
  
  const handleDeleteBook = async (bookId: string) => {
    try {
      // Set up token provider for authenticated requests
      const tokenProvider = async () => session?.session.token || null;
      bookClient.setTokenProvider(tokenProvider);

      await bookClient.deleteBook(bookId);
      toast.success('Book deleted successfully');

      // Update the local state to remove the deleted book
      setProjects(prevProjects => prevProjects.filter(book => book.id !== bookId));
    } catch (err) {
      console.error('Error deleting book:', err);
      toast.error('Failed to delete book. Please try again.');
    }
  };

  // Show loading state
  if (isLoading) {
    return (
      <div className="container mx-auto flex-1 p-6 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
          <p className="text-gray-400">Loading your books...</p>
        </div>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="container mx-auto flex-1 p-6 flex items-center justify-center">
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-6 max-w-md">
          <h2 className="text-red-400 text-xl font-medium mb-2">Error</h2>
          <p className="text-gray-300 mb-4">{error}</p>
          <Button
            onClick={() => fetchBooks()}
            className="bg-red-600 hover:bg-red-700 text-white"
          >
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="container mx-auto flex-1 p-6">
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-2">
            <HugeiconsIcon icon={Book02Icon} size={32} className="text-indigo-400" />
            <h2 className="text-3xl font-bold text-gray-100">My Books</h2>
          </div>
          <Button
            onClick={handleCreateNewBook}
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            <HugeiconsIcon icon={Add01Icon} size={20} className="mr-2" />
            Create New Book
          </Button>
        </div>

        {/* Projects Grid */}
        {projects.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map(project => (
              <BookCard
                key={project.id}
                book={project}
                onDelete={handleDeleteBook}
              />
            ))}
          </div>
        ) : (
          <EmptyBookState onCreateNew={handleCreateNewBook} />
        )}
      </div>

      {/* Book creation wizard */}
      <BookCreationWizard
        isOpen={isBookDialogOpen}
        onOpenChange={setIsBookDialogOpen}
        onSuccess={handleBookCreated}
      />
    </>
  );
}

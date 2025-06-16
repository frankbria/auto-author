'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { useUser, useAuth } from '@clerk/nextjs';
import { Button } from '@/components/ui/button';
import { PlusIcon, BookIcon } from 'lucide-react';
import BookCard, { BookProject } from '@/components/BookCard';
import { BookCreationWizard } from '@/components/BookCreationWizard';
import { EmptyBookState } from '@/components/EmptyBookState';
import bookClient from '@/lib/api/bookClient';

export default function Dashboard() {
  const router = useRouter();
  const { user, isLoaded: isUserLoaded } = useUser();
  const { getToken } = useAuth();
  const [projects, setProjects] = useState<BookProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isBookDialogOpen, setIsBookDialogOpen] = useState(false);

  const fetchBooks = useCallback(async () => {
    if (!isUserLoaded || !user) return;
    setIsLoading(true);
    try {
      // Get Clerk session token for API authentication
      const token = await getToken();
      if (token) {
        bookClient.setAuthToken(token);
      }
      const books = await bookClient.getUserBooks();
      setProjects(books);
      setError(null);
    } catch (err) {
      console.error('Error fetching books:', err);
      setError('Failed to load your books. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [isUserLoaded, user, getToken]);

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
      // Get Clerk session token for API authentication
      const token = await getToken();
      if (token) {
        bookClient.setAuthToken(token);
      }
      
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
          <p className="text-zinc-400">Loading your books...</p>
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
          <p className="text-zinc-300 mb-4">{error}</p>
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
            <BookIcon className="h-8 w-8 text-indigo-400" />
            <h2 className="text-3xl font-bold text-zinc-100">My Books</h2>
          </div>
          <Button 
            onClick={handleCreateNewBook}
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
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

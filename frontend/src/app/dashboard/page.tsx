'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import BookCard, { BookProject } from '@/components/BookCard';
import { useUser } from '@clerk/nextjs';
import bookClient from '@/lib/api/bookClient';

export default function Dashboard() {
  const router = useRouter();
  const { user, isLoaded: isUserLoaded } = useUser();
  const [projects, setProjects] = useState<BookProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    // Only fetch books when user is loaded
    if (isUserLoaded && user) {
      setIsLoading(true);
      
      // In a real app, we could set the auth token first
      // bookClient.setAuthToken(user.getToken());
      
      bookClient.getUserBooks()
        .then((books: BookProject[]) => {
          setProjects(books);
          setError(null);
        })
        .catch((err: Error) => {
          console.error('Error fetching books:', err);
          setError('Failed to load your books. Please try again.');
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, [isUserLoaded, user]);

  const handleCreateNewBook = () => {
    // Navigate to the book creation page
    router.push('/dashboard/new-book');
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
          <button 
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-md"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto flex-1 p-6">
      <div className="flex justify-between items-center mb-8">
        <h2 className="text-3xl font-bold text-zinc-100">My Books</h2>
        <button 
          onClick={handleCreateNewBook}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md flex items-center"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
          </svg>
          Create New Book
        </button>
      </div>

      {/* Projects Grid */}
      {projects.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map(project => (
            <BookCard key={project.id} book={project} />
          ))}
        </div>
      ) : (
        <div className="text-center p-12 bg-zinc-800/50 rounded-lg border border-zinc-700">
          <h3 className="text-xl font-medium text-zinc-300 mb-2">No book projects yet</h3>
          <p className="text-zinc-400 mb-6">Create your first book project to get started</p>
          <button 
            onClick={handleCreateNewBook}
            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md"
          >
            Create Your First Book
          </button>
        </div>
      )}
    </div>
  );
}


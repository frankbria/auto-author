'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from '@/lib/toast';
import { useSession } from '@/lib/auth-client';
import { Button } from '@/components/ui/button';
import { HugeiconsIcon } from '@hugeicons/react';
import {
  Add01Icon,
  ArrowLeft01Icon,
  ArrowRight01Icon,
  Book02Icon,
} from '@hugeicons/core-free-icons';
import BookCard, { BookProject } from '@/components/BookCard';
import { BookCreationWizard } from '@/components/BookCreationWizard';
import { EmptyBookState } from '@/components/EmptyBookState';
import { Skeleton } from '@/components/ui/skeleton';
import bookClient from '@/lib/api/bookClient';

/**
 * Books per page. The endpoint caps `limit` at 100 and the dashboard used to request
 * all 100 with no way to reach anything past them (#493). 24 divides evenly into the
 * 1/2/3-column grid and cuts the first-paint payload from ~195 KB to ~49 KB.
 */
const PAGE_SIZE = 24;

export default function Dashboard() {
  const router = useRouter();
  const { data: session, isPending: isSessionPending } = useSession();
  const [projects, setProjects] = useState<BookProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isBookDialogOpen, setIsBookDialogOpen] = useState(false);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  // The loading branch below is a full-page early return. Gating it on "nothing has
  // ever loaded" keeps the pager mounted while a later page is in flight, instead of
  // replacing the whole screen with a skeleton on every Next click.
  const hasLoadedOnce = useRef(false);

  // E2E test mode detection
  const isE2EMode = process.env.NEXT_PUBLIC_BYPASS_AUTH === 'true';

  const fetchBooks = useCallback(async () => {
    // In E2E mode, bypass session user check
    if (!isE2EMode && (!session)) return;

    setIsLoading(true);
    try {
      // Cookie-based authentication - no token provider needed
      // Cookies are automatically sent with credentials: 'include'
      // Over-fetch a single row past the page: the endpoint returns a bare array with
      // no total, so the presence of that extra row is how we learn a next page exists
      // without paying a second count query.
      const fetched = await bookClient.getUserBooks({
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE + 1,
      });
      setHasMore(fetched.length > PAGE_SIZE);
      setProjects(fetched.slice(0, PAGE_SIZE));
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
      hasLoadedOnce.current = true;
    }
  }, [session, isE2EMode, page]);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  const handleCreateNewBook = () => {
    setIsBookDialogOpen(true);
  };

  const handleBookCreated = (bookId: string) => {
    toast.success({ title: 'Your book has been created! Click "Open Project" to start writing.' });
    // The list is newest-first, so a new book lands on page 1. Jumping there lets the
    // page-change effect do the refetch; on page 1 already, refetch directly.
    if (page === 0) {
      fetchBooks();
    } else {
      setPage(0);
    }

    // Redirect after a short delay to allow the user to see the success toast
    setTimeout(() => {
      router.push(`/dashboard/books/${bookId}`);
    }, 1500);
  };

  const handleDeleteBook = async (bookId: string) => {
    try {
      // Cookie-based authentication - no token provider needed
      await bookClient.deleteBook(bookId);
      toast.success({ title: 'Book deleted successfully' });

      // Update the local state to remove the deleted book
      setProjects(prevProjects => prevProjects.filter(book => book.id !== bookId));

      // On a single-page library the splice above is the whole story. Once the list is
      // paged it is not: the row that shifts up from the next page was never fetched,
      // and deleting the last book on a later page strands the user on a blank one.
      if (page > 0 && projects.length === 1) {
        setPage(prevPage => prevPage - 1);  // page-change effect refetches
      } else if (hasMore || page > 0) {
        await fetchBooks();
      }
    } catch (err) {
      console.error('Error deleting book:', err);
      toast.error({ title: 'Failed to delete book. Please try again.' });
    }
  };

  // Show loading state — skeleton mirroring the book-card grid to prevent layout shift
  if (isLoading && !hasLoadedOnce.current) {
    return (
      <div
        className="container mx-auto flex-1 p-6"
        role="status"
        aria-live="polite"
        aria-busy="true"
        data-testid="dashboard-skeleton"
      >
        <span className="sr-only">Loading your books...</span>
        <div className="flex justify-between items-center mb-8">
          <Skeleton className="h-9 w-48" />
          <Skeleton className="h-10 w-40" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full rounded-lg" />
          ))}
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
          <p className="text-muted-foreground mb-4">{error}</p>
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
            <h2 className="text-3xl font-bold text-foreground">My Books</h2>
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
          <div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            aria-busy={isLoading}
          >
            {projects.map(project => (
              <BookCard
                key={project.id}
                book={project}
                onDelete={handleDeleteBook}
              />
            ))}
          </div>
        ) : page === 0 ? (
          <EmptyBookState onCreateNew={handleCreateNewBook} />
        ) : (
          // An empty *later* page is not an empty library — showing the onboarding
          // "create your first book" state here would be a lie.
          <p className="text-muted-foreground">No books on this page.</p>
        )}

        {(page > 0 || hasMore) && (
          <nav
            aria-label="Book list pagination"
            className="mt-8 flex items-center justify-center gap-4"
          >
            <Button
              variant="outline"
              aria-label="Previous page"
              disabled={page === 0 || isLoading}
              onClick={() => setPage(prevPage => Math.max(0, prevPage - 1))}
            >
              <HugeiconsIcon icon={ArrowLeft01Icon} size={20} className="mr-2" />
              Previous
            </Button>
            <span aria-live="polite" className="text-sm text-muted-foreground">
              Page {page + 1}
            </span>
            <Button
              variant="outline"
              aria-label="Next page"
              disabled={!hasMore || isLoading}
              onClick={() => setPage(prevPage => prevPage + 1)}
            >
              Next
              <HugeiconsIcon icon={ArrowRight01Icon} size={20} className="ml-2" />
            </Button>
          </nav>
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

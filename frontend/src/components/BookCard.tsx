'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Card, CardContent, CardFooter, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { HugeiconsIcon } from '@hugeicons/react';
import { Delete02Icon } from '@hugeicons/core-free-icons';
import { DeleteBookModal } from '@/components/books';

export type BookProject = {
  id: string;
  title: string;
  description?: string;
  subtitle?: string;
  genre?: string;
  target_audience?: string;
  cover_image_url?: string;
  created_at?: string;
  updated_at?: string;
  published?: boolean;
  collaborators?: Record<string, unknown>[];
  owner_id?: string;
  chapters: number; // computed from toc_items.length
  progress: number; // computed
  word_count?: number; // total word count across all chapters
};

type BookCardProps = {
  book: BookProject;
  onClick?: () => void;
  onDelete?: (bookId: string) => void;
};

export default function BookCard({ book, onClick, onDelete }: BookCardProps) {
  const router = useRouter();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const formatDate = (dateString: string) => {
    if (!dateString) {
      return 'Never';
    }
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return 'Never';
    }
    // Use UTC date to avoid timezone conversion issues
    // This ensures the displayed date matches the stored UTC date
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      timeZone: 'UTC'
    });
  };

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      router.push(`/dashboard/books/${book.id}`);
    }
  };

  const handleDelete = async () => {
    if (!onDelete) return;

    setIsDeleting(true);
    try {
      await onDelete(book.id);
      setShowDeleteDialog(false);
    } catch (error) {
      console.error('Failed to delete book:', error);
      // Error handling is done in parent component
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      <Card
        data-testid="book-card"
        className="w-full max-w-[350px] bg-gray-800 border border-gray-700 hover:border-indigo-500 transition cursor-pointer"
        onClick={handleClick}
      >
      <div className="p-5">
        <CardTitle className="text-xl font-semibold text-gray-100 mb-2 truncate" title={book.title}>
          {book.title}
        </CardTitle>
      </div>
        <CardContent>
        {book.description && (
          <p className="text-gray-400 text-sm mb-3 line-clamp-2" title={book.description}>
            {book.description}
          </p>
        )}

        <div className="flex items-center text-sm text-gray-400 mb-4">
          <span>Last edited {formatDate(book.updated_at ?? book.created_at ?? '')}</span>
          <span className="mx-2">•</span>
          <span>
            {book.chapters === 0 ? (
              <span className="text-indigo-400">New</span>
            ) : (
              `${book.chapters} chapters`
            )}
          </span>
        </div>

        {book.chapters === 0 ? (
          <div className="bg-indigo-900/20 border border-indigo-800/50 rounded-md p-3 mb-4">
            <p className="text-indigo-300 text-sm font-medium">
              Ready to start writing! Click below to begin creating your book content.
            </p>
          </div>
        ) : (
          <div className="mb-4">
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div
                className="bg-indigo-600 h-2 rounded-full"
                style={{ width: `${book.progress}%` }}
              ></div>
            </div>
            <div className="flex justify-between mt-1 text-sm text-gray-400">
              <span>Progress</span>
              <span>{book.progress}%</span>
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="px-5 pt-0 flex gap-2">
        <Button
          className="flex-1 bg-gray-700 hover:bg-indigo-600 text-gray-100 h-11"
          onClick={(e) => {
            e.stopPropagation();
            router.push(`/dashboard/books/${book.id}`);
          }}
        >
          Open Project
        </Button>
        {onDelete && (
          <Button
            className="bg-gray-700 hover:bg-red-600 text-gray-100 h-11 w-11"
            onClick={(e) => {
              e.stopPropagation();
              setShowDeleteDialog(true);
            }}
            disabled={isDeleting}
            aria-label="Delete book"
          >
            <HugeiconsIcon icon={Delete02Icon} size={16} data-testid="trash-icon" />
          </Button>
        )}
      </CardFooter>
      </Card>

      <DeleteBookModal
        isOpen={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        bookTitle={book.title}
        bookStats={{
          chapterCount: book.chapters,
          wordCount: book.word_count ?? 0,
        }}
        onConfirm={handleDelete}
        isDeleting={isDeleting}
      />
    </>
  );
}

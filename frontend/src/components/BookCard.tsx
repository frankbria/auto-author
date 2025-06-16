'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Card, CardContent, CardFooter, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Trash2 } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

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
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
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
        className="w-[350px] bg-zinc-800 border border-zinc-700 hover:border-indigo-500 transition cursor-pointer"
        onClick={handleClick}
      >
      <div className="p-5">
        <CardTitle className="text-xl font-semibold text-zinc-100 mb-2 truncate" title={book.title}>
          {book.title}
        </CardTitle>
      </div>
        <CardContent>
        {book.description && (
          <p className="text-zinc-400 text-sm mb-3 line-clamp-2" title={book.description}>
            {book.description}
          </p>
        )}
        
        <div className="flex items-center text-sm text-zinc-400 mb-4">
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
            <div className="w-full bg-zinc-700 rounded-full h-2">
              <div 
                className="bg-indigo-600 h-2 rounded-full" 
                style={{ width: `${book.progress}%` }}
              ></div>
            </div>
            <div className="flex justify-between mt-1 text-sm text-zinc-400">
              <span>Progress</span>
              <span>{book.progress}%</span>
            </div>
          </div>
        )}
      </CardContent>
      
      <CardFooter className="px-5 pt-0 flex gap-2">
        <Button
          className="flex-1 bg-zinc-700 hover:bg-indigo-600 text-zinc-100"
          onClick={(e) => {
            e.stopPropagation();
            router.push(`/dashboard/books/${book.id}`);
          }}
        >
          Open Project
        </Button>
        {onDelete && (
          <Button
            className="bg-zinc-700 hover:bg-red-600 text-zinc-100"
            size="icon"
            onClick={(e) => {
              e.stopPropagation();
              setShowDeleteDialog(true);
            }}
            disabled={isDeleting}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </CardFooter>
      </Card>
      
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete Book</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete "{book.title}"? This action cannot be undone.
            All chapters and content will be permanently deleted.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleDelete}
            disabled={isDeleting}
            className="bg-red-600 hover:bg-red-700"
          >
            {isDeleting ? 'Deleting...' : 'Delete'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
    </>
  );
}

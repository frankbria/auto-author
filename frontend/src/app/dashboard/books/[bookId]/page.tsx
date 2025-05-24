'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import bookClient from '@/lib/api/bookClient';
import { BookProject } from '@/components/BookCard';
import * as React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { bookCreationSchema, BookFormData } from '@/lib/schemas/bookSchema';
import { toast } from 'sonner';
import Image from 'next/image';
import { BookMetadataForm } from '@/components/BookMetadataForm';

// Define types for book data
type Chapter = {
  id: string;
  title: string;
  completed: boolean;
  wordCount: number;
  progress: number;
};

type BookDetails = Omit<BookProject, 'chapters'> & {
  description: string;
  chapters: Chapter[];
  subtitle?: string;
  genre?: string;
  target_audience?: string;
  cover_image_url?: string;
  created_at?: string;
  updated_at?: string;
  published?: boolean;
  collaborators?: Record<string, unknown>[];
  owner_id?: string;
  summary?: string; // Add summary for wizard logic
};

// Sample chapters data - would come from API in production
const SAMPLE_CHAPTERS: Chapter[] = [
  {
    id: 'ch-1',
    title: 'Introduction to Machine Learning',
    completed: true,
    wordCount: 2500,
    progress: 100
  },
  {
    id: 'ch-2',
    title: 'Supervised Learning Algorithms',
    completed: true,
    wordCount: 3200,
    progress: 100
  },
  {
    id: 'ch-3',
    title: 'Unsupervised Learning Techniques',
    completed: false,
    wordCount: 1800,
    progress: 70
  },
  {
    id: 'ch-4',
    title: 'Neural Networks Fundamentals',
    completed: false,
    wordCount: 800,
    progress: 25
  },
  {
    id: 'ch-5',
    title: 'Advanced Deep Learning',
    completed: false,
    wordCount: 0,
    progress: 0
  }
];

export default function BookPage({ params }: { params: Promise<{ bookId: string }> }) {
  const router = useRouter();
  const [book, setBook] = useState<BookDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [summary, setSummary] = useState('');

  // Unwrap params using React.use (Next.js 15+)
  const { bookId } = React.use(params);
  
  useEffect(() => {
    setIsLoading(true);
    // Fetch book details
    bookClient.getBook(bookId)
      .then((bookData: BookProject) => {
        setBook({
          ...bookData,
          description: bookData.description || 'No description available',
          subtitle: bookData.subtitle,
          genre: bookData.genre,
          target_audience: bookData.target_audience,
          cover_image_url: bookData.cover_image_url,
          created_at: bookData.created_at,
          updated_at: bookData.updated_at,
          published: bookData.published,
          collaborators: bookData.collaborators,
          owner_id: bookData.owner_id,
          chapters: SAMPLE_CHAPTERS,
          summary: undefined, // will be set below
        });
        setError(null);
      })
      .catch((err: Error) => {
        console.error('Error fetching book details:', err);
        setError('Failed to load book details. Please try again.');
      })
      .finally(() => {
        setIsLoading(false);
      });
    // Fetch summary for wizard step logic
    bookClient.getBookSummary(bookId)
      .then((data) => {
        setSummary(data.summary || '');
        setBook((prev) => prev ? { ...prev, summary: data.summary || '' } : prev);
      })
      .catch(() => {
        setSummary('');
        setBook((prev) => prev ? { ...prev, summary: '' } : prev);
      });
  }, [bookId]);
    const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  const handleCreateChapter = () => {
    // In production, this would open a dialog or navigate to chapter creation
    alert('Create new chapter functionality coming soon!');
  };
  
  const handleEditChapter = (chapterId: string) => {
    // Navigate to chapter edit page
    router.push(`/dashboard/books/${bookId}/chapters/${chapterId}`);
  };

  const form = useForm<BookFormData>({
    resolver: zodResolver(bookCreationSchema),
    defaultValues: {
      title: book?.title || '',
      subtitle: book?.subtitle || '',
      description: book?.description || '',
      genre: book?.genre || '',
      target_audience: book?.target_audience || '',
      cover_image_url: book?.cover_image_url || '',
    },
    mode: 'onChange',
  });

  // Auto-save on change
  useEffect(() => {
    if (!book) return;
    form.reset({
      title: book.title,
      subtitle: book.subtitle,
      description: book.description,
      genre: book.genre,
      target_audience: book.target_audience,
      cover_image_url: book.cover_image_url,
    });  }, [book, form]);

  const [isSaving, setIsSaving] = useState(false);
  // Auto-save on form change
  useEffect(() => {
    const subscription = form.watch(async (values) => {
      if (!book) return;
      setIsSaving(true);
      try {
        await bookClient.updateBook(book.id, {
          title: values.title,
          subtitle: values.subtitle,
          description: values.description,
          genre: values.genre,
          target_audience: values.target_audience,
          cover_image_url: values.cover_image_url,
        });
        toast.success('Book info saved');
        setHasCommitted(true);
      } catch {
        toast.error('Failed to save book info');
      } finally {
        setIsSaving(false);
      }
    });
    return () => subscription.unsubscribe();
  }, [book, form]);

  // Show loading state
  if (isLoading) {
    return (
      <div className="container mx-auto flex-1 p-6 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
          <p className="text-zinc-400">Loading book details...</p>
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
          <div className="flex space-x-4">
            <button 
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-md"
            >
              Try Again
            </button>
            <Link 
              href="/dashboard" 
              className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-white font-medium rounded-md"
            >
              Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }
  
  // If book is null but not loading or error state
  if (!book) {
    return (
      <div className="container mx-auto flex-1 p-6 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-medium text-zinc-300 mb-4">Book not found</h2>
          <Link 
            href="/dashboard" 
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto flex-1 p-6">
      <div className="mb-6">
        <Link 
          href="/dashboard" 
          className="text-indigo-400 hover:text-indigo-300 flex items-center gap-2 mb-4"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M9.707 14.707a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 1.414L7.414 9H15a1 1 0 110 2H7.414l2.293 2.293a1 1 0 010 1.414z" clipRule="evenodd" />
          </svg>
          Back to Dashboard
        </Link>
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-zinc-100">{book.title}</h1>
          <div className="text-zinc-400 text-sm">
            Last edited {formatDate(book.updated_at ?? book.created_at ?? '')}
          </div>
        </div>
        {/* Wizard/Stepper Actions */}
        <div className="mt-8 mb-8">
          <div className="flex flex-col md:flex-row md:items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="flex flex-col items-center">
                <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold">1</div>
                <div className="h-8 w-1 bg-indigo-300/30 md:h-1 md:w-8 md:mx-2 md:my-0 my-2"></div>
              </div>
              <div>
                <div className="font-semibold text-zinc-100">Book Summary</div>
                <div className="text-xs text-zinc-400">Describe your book&apos;s main idea and structure</div>
                <Link href={`/dashboard/books/${bookId}/summary`}>
                  <button className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md">
                    Start with Book Summary
                  </button>
                </Link>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full ${book?.summary && book.summary.length >= 30 ? 'bg-indigo-600 text-white' : 'bg-zinc-700 text-zinc-400 border border-zinc-500'} flex items-center justify-center font-bold`}>2</div>
              </div>
              <div>
                <div className="font-semibold text-zinc-100">Generate TOC</div>
                <div className="text-xs text-zinc-400">AI generates a Table of Contents from your summary</div>
                {book?.summary && book.summary.length >= 30 ? (
                  <Link href={`./generate-toc`}>
                    <button className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md">
                      Generate TOC
                    </button>
                  </Link>
                ) : (
                  <button className="mt-2 px-4 py-2 bg-zinc-700 text-zinc-400 font-medium rounded-md cursor-not-allowed" disabled>
                    Complete Book Summary First
                  </button>
                )}
              </div>
            </div>
            <div className="flex-1"></div>
          </div>
        </div>
        {/* End Wizard/Stepper Actions */}
        {!editMode ? (
          <>
            {book.cover_image_url && (
              <div className="mt-4">
                <Image src={book.cover_image_url} alt="Book cover" width={256} height={384} className="max-w-xs rounded shadow border border-zinc-700" />
              </div>
            )}
            <div className="mt-2">
              {book.subtitle && <div className="text-zinc-300 text-lg italic mb-1">{book.subtitle}</div>}
              <div className="text-zinc-400 max-w-3xl mb-2">{book.description}</div>
              {book.genre && <div className="text-zinc-400 text-sm">Genre: {book.genre}</div>}
              {book.target_audience && <div className="text-zinc-400 text-sm">Audience: {book.target_audience}</div>}
            </div>
            <button
              className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md"
              onClick={() => setEditMode(true)}
            >
              Edit Book
            </button>
          </>
        ) : (
          <>
            <BookMetadataForm
              book={{
                title: book.title || '',
                subtitle: book.subtitle || '',
                description: book.description || '',
                genre: book.genre || '',
                target_audience: book.target_audience || '',
                cover_image_url: book.cover_image_url || '',
              }}
              onUpdate={async (values) => {
                setIsSaving(true);
                try {
                  await bookClient.updateBook(book.id, values);
                  toast.success('Book info saved');
                  setBook({ ...book, ...values });
                } catch {
                  toast.error('Failed to save book info');
                } finally {
                  setIsSaving(false);
                }
              }}
              isSaving={isSaving}
              error={error}
            />
            <button
              className="mt-4 px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-md"
              onClick={() => setEditMode(false)}
            >
              Cancel
            </button>
          </>
        )}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-zinc-800 border border-zinc-700 p-5 rounded-lg lg:col-span-3">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-semibold text-zinc-100">Chapters</h2>
            <button 
              onClick={handleCreateChapter}
              className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-md flex items-center"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
              </svg>
              Add Chapter
            </button>
          </div>
          <div className="space-y-3">
            {book.chapters.map((chapter, index) => (
              <div 
                key={chapter.id} 
                className="p-4 bg-zinc-750 border border-zinc-700 rounded-md hover:border-indigo-500 transition cursor-pointer"
                onClick={() => handleEditChapter(chapter.id)}
              >
                <div className="flex justify-between items-center">
                  <div>
                    <div className="flex items-center">
                      <span className="text-zinc-500 mr-2">#{index + 1}</span>
                      <h3 className="font-medium text-zinc-100">
                        {chapter.title}
                        {chapter.completed && (
                          <span className="ml-2 px-2 py-0.5 bg-green-900/30 text-green-400 text-xs rounded-full">
                            Completed
                          </span>
                        )}
                      </h3>
                    </div>
                    <div className="text-zinc-400 text-sm mt-1">
                      {chapter.wordCount > 0 ? `${chapter.wordCount.toLocaleString()} words` : 'No content yet'}
                    </div>
                  </div>
                  <div className="flex flex-col items-end">
                    <div className="text-sm text-zinc-400">{chapter.progress}% complete</div>
                    <div className="w-24 bg-zinc-700 rounded-full h-1.5 mt-1">
                      <div 
                        className={`h-1.5 rounded-full ${chapter.completed ? 'bg-green-500' : 'bg-indigo-600'}`}
                        style={{ width: `${chapter.progress}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {book.chapters.length === 0 && (
              <div className="text-center p-8 bg-zinc-800/50 rounded-lg border border-zinc-700">
                <p className="text-zinc-400 mb-4">No chapters yet. Create your first one to get started.</p>
                <button 
                  onClick={handleCreateChapter}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md"
                >
                  Create First Chapter
                </button>
              </div>
            )}
          </div>
        </div>
        <div className="bg-zinc-800 border border-zinc-700 p-5 rounded-lg">
          <h2 className="text-xl font-semibold text-zinc-100 mb-4">Book Stats</h2>
          <div className="space-y-3">
            <div>
              <div className="text-sm text-zinc-400 mb-1">Overall Progress</div>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-zinc-700 rounded-full h-2">
                  <div 
                    className="bg-indigo-600 h-2 rounded-full" 
                    style={{ width: `${book.progress}%` }}
                  ></div>
                </div>
                <span className="text-zinc-300">{book.progress}%</span>
              </div>
            </div>
            <div className="pt-2">
              <div className="text-sm text-zinc-400 mb-1">Chapters</div>
              <div className="text-zinc-100 font-medium">{book.chapters.length}</div>
            </div>
            <div className="pt-2">
              <div className="text-sm text-zinc-400 mb-1">Total Word Count</div>
              <div className="text-zinc-100 font-medium">
                {book.chapters.reduce((sum, chapter) => sum + chapter.wordCount, 0).toLocaleString()}
              </div>
            </div>
            <div className="pt-2">
              <div className="text-sm text-zinc-400 mb-1">Completed Chapters</div>
              <div className="text-zinc-100 font-medium">
                {book.chapters.filter(ch => ch.completed).length} of {book.chapters.length}
              </div>
            </div>
          </div>
          <div className="mt-6 pt-4 border-t border-zinc-700">
            <button className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md">
              Generate PDF Preview
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
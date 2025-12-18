'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useSession } from '@/lib/auth-client';
import { useSearchParams } from 'next/navigation';
import bookClient from '@/lib/api/bookClient';
import { BookProject } from '@/components/BookCard';
import { TocData } from '@/types/toc';
import * as React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { bookCreationSchema, BookFormData } from '@/lib/schemas/bookSchema';
import { toast } from 'sonner';
import Image from 'next/image';
import { BookMetadataForm } from '@/components/BookMetadataForm';
import { ChapterTabs } from '@/components/chapters/ChapterTabs';
import { ChapterBreadcrumb } from '@/components/navigation/ChapterBreadcrumb';
import { ExportOptionsModal } from '@/components/export/ExportOptionsModal';
import { ExportProgressModal } from '@/components/export/ExportProgressModal';
import { downloadBlob, generateFilename, formatFileSize } from '@/components/export/exportHelpers';
import { ExportOptions, ExportStatus } from '@/types/export';
import { handleApiCall } from '@/lib/errors';
import { showErrorNotification, showRecoveryNotification } from '@/components/errors';

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

// Helper function to convert TOC data to Chapter format for UI
const convertTocToChapters = (tocData: TocData | null): Chapter[] => {
  if (!tocData || !tocData.chapters) {
    return [];
  }

  const chapters: Chapter[] = [];
  
  tocData.chapters.forEach((tocChapter) => {
    // Add main chapter
    const chapter: Chapter = {
      id: tocChapter.id,
      title: tocChapter.title,
      completed: false, // Default to false since we don't have content yet
      wordCount: 0, // Default to 0 since we don't have content yet
      progress: 0, // Default to 0 since we don't have content yet
    };
    chapters.push(chapter);

    // Add subchapters if they exist
    if (tocChapter.subchapters && tocChapter.subchapters.length > 0) {
      tocChapter.subchapters.forEach((subchapter) => {
        const subChapter: Chapter = {
          id: subchapter.id,
          title: subchapter.title,
          completed: false,
          wordCount: 0,
          progress: 0,
        };
        chapters.push(subChapter);
      });
    }
  });

  return chapters;
};

export default function BookPage({ params }: { params: Promise<{ bookId: string }> }) {
  const { data: session } = useSession();
  const searchParams = useSearchParams();
  const initialChapter = searchParams.get('chapter');

  const [book, setBook] = useState<BookDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);

  // Unwrap params using React.use (Next.js 15+)
  const { bookId } = React.use(params);

  useEffect(() => {
    const fetchBookData = async () => {
      setIsLoading(true);
      try {
        // Set up token provider for automatic token refresh
        const tokenProvider = async () => session?.session.token || null;
        bookClient.setTokenProvider(tokenProvider);

        // Fetch book details
        const bookData: BookProject = await bookClient.getBook(bookId);
        // Fetch TOC data to populate chapters
        let chapters: Chapter[] = [];
        try {
          const tocResponse = await bookClient.getToc(bookId);
          chapters = convertTocToChapters(tocResponse.toc as TocData);
        } catch (tocError) {
          console.warn('No TOC found for this book yet:', tocError);
        }

        // Always fetch summary from API
        let summary = '';
        try {
          const summaryResponse = await bookClient.getBookSummary(bookId);
          if (summaryResponse && summaryResponse.summary) {
            summary = summaryResponse.summary;
          }
        } catch {
          summary = '';
        }

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
          chapters: chapters,
          summary: summary,
        });
        setError(null);
      } catch (err: unknown) {
        console.error('Error fetching book details:', err);
        setError('Failed to load book details. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchBookData();
  }, [bookId, session]);
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

  // Export modal states
  const [showExportOptions, setShowExportOptions] = useState(false);
  const [showExportProgress, setShowExportProgress] = useState(false);
  const [exportStatus, setExportStatus] = useState<ExportStatus>('pending');
  const [exportProgress, setExportProgress] = useState(0);
  const [exportError, setExportError] = useState<string | undefined>();
  const [exportFilename, setExportFilename] = useState<string | undefined>();

  const handleExportClick = () => {
    setShowExportOptions(true);
  };

  const handleExport = async (options: ExportOptions) => {
    if (!book) return;

    // Close options modal and open progress modal
    setShowExportOptions(false);
    setShowExportProgress(true);
    setExportStatus('pending');
    setExportProgress(0);
    setExportError(undefined);

    // Update status to processing
    setExportStatus('processing');

    // Simulate progress (in real implementation, this would come from backend)
    const progressInterval = setInterval(() => {
      setExportProgress((prev) => {
        if (prev >= 90) return prev;
        return prev + 10;
      });
    }, 500);

    // Call appropriate export method with error handling
    const result = await handleApiCall(
      async () => {
        if (options.format === 'pdf') {
          return await bookClient.exportPDF(bookId, {
            includeEmptyChapters: options.includeEmptyChapters,
            pageSize: options.pageSize,
          });
        } else {
          return await bookClient.exportDOCX(bookId, {
            includeEmptyChapters: options.includeEmptyChapters,
          });
        }
      },
      {
        context: `Export ${options.format.toUpperCase()}`,
        onRetry: (attempt, error) => {
          setExportProgress(0);
          toast.info(`Retrying export (attempt ${attempt})...`);
        },
        onSuccess: (attempts) => {
          if (attempts > 1) {
            showRecoveryNotification('Export completed', attempts);
          }
        },
      }
    );

    clearInterval(progressInterval);

    if (result.success && result.data) {
      // Success!
      setExportProgress(100);

      // Generate filename and download
      const filename = generateFilename(book.title, options.format);
      setExportFilename(filename);
      downloadBlob(result.data, filename);

      // Update status to completed
      setExportStatus('completed');
      toast.success(`${options.format.toUpperCase()} exported successfully!`);
    } else if (result.error) {
      // Error occurred
      setExportStatus('failed');
      setExportError(result.error.message);

      // Show error notification with retry capability
      showErrorNotification(result.error, {
        onRetry: handleRetryExport,
      });
    }
  };

  const handleCloseExportProgress = () => {
    setShowExportProgress(false);
    setExportProgress(0);
    setExportStatus('pending');
    setExportError(undefined);
    setExportFilename(undefined);
  };

  const handleRetryExport = () => {
    setShowExportProgress(false);
    setShowExportOptions(true);
  };
  // Auto-save on form change
  useEffect(() => {
    const subscription = form.watch(async (values) => {
      if (!book) return;
      setIsSaving(true);
      try {        await bookClient.updateBook(book.id, {
          title: values.title,
          subtitle: values.subtitle,
          description: values.description,
          genre: values.genre,
          target_audience: values.target_audience,
          cover_image_url: values.cover_image_url,
        });
        toast.success('Book info saved');
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
      {/* Breadcrumb Navigation */}
      {(() => {
        // Get active chapter info for breadcrumb
        const activeChapter = initialChapter ? book.chapters.find(ch => ch.id === initialChapter) : null;
        const showChapterContext = !!initialChapter && !!activeChapter;
        
        return (
          <ChapterBreadcrumb
            bookId={book.id}
            bookTitle={book.title}
            chapterId={initialChapter || undefined}
            chapterTitle={activeChapter?.title}
            showChapterContext={showChapterContext}
          />
        );
      })()}
      
      <div className="mb-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-zinc-100">{book.title}</h1>
          <div className="flex items-center gap-4">
            <button
              onClick={handleExportClick}
              className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors flex items-center gap-2 shadow-lg"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
              </svg>
              Export Book
            </button>
            <div className="text-zinc-400 text-sm">
              Last edited {formatDate(book.updated_at ?? book.created_at ?? '')}
            </div>
          </div>
        </div>        {/* Wizard/Stepper Actions */}
        <div className="mt-8 mb-8">
          <div className="flex flex-col md:flex-row md:items-center gap-4">
            {/* Step 1: Book Summary */}
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
                    {book?.summary && book.summary.length >= 30 ? 'Edit Book Summary' : 'Start with Book Summary'}
                  </button>
                </Link>
              </div>
            </div>
            {/* Step 2: TOC Generation */}
            <div className="flex items-center gap-3">
              <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full ${(book?.summary && book.summary.length >= 30) ? 'bg-indigo-600 text-white' : 'bg-zinc-700 text-zinc-400 border border-zinc-500'} flex items-center justify-center font-bold`}>2</div>
                <div className="h-8 w-1 bg-indigo-300/30 md:h-1 md:w-8 md:mx-2 md:my-0 my-2"></div>
              </div>
              <div>
                <div className="font-semibold text-zinc-100">Generate TOC</div>
                <div className="text-xs text-zinc-400">AI generates a Table of Contents from your summary</div>
                {book?.summary && book.summary.length >= 30 ? (
                  book.chapters && book.chapters.length > 0 ? (
                    <Link href={`/dashboard/books/${bookId}/edit-toc`}>
                      <button className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md">
                        Edit TOC
                      </button>
                    </Link>
                  ) : (
                    <Link href={`./generate-toc`}>
                      <button className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md">
                        Generate TOC
                      </button>
                    </Link>
                  )
                ) : (
                  <button className="mt-2 px-4 py-2 bg-zinc-700 text-zinc-400 font-medium rounded-md cursor-not-allowed" disabled>
                    Complete Book Summary First
                  </button>
                )}
              </div>
            </div>
            {/* Step 3: Write Content */}
            <div className="flex items-center gap-3">
              <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full ${(book?.summary && book.summary.length >= 30 && book.chapters && book.chapters.length > 0) ? 'bg-indigo-600 text-white' : 'bg-zinc-700 text-zinc-400 border border-zinc-500'} flex items-center justify-center font-bold`}>3</div>
              </div>
              <div>
                <div className="font-semibold text-zinc-100">Write Content</div>
                <div className="text-xs text-zinc-400">Write and edit your chapter content</div>
                {(book?.summary && book.summary.length >= 30 && book.chapters && book.chapters.length > 0) ? (
                  <div className="mt-2 text-sm text-green-400">
                    ✓ Ready to write! Use the tabs below to start writing your chapters.
                  </div>
                ) : (
                  <button className="mt-2 px-4 py-2 bg-zinc-700 text-zinc-400 font-medium rounded-md cursor-not-allowed" disabled>
                    {book?.summary && book.summary.length >= 30 ? 'Generate TOC First' : 'Complete Book Summary First'}
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
      </div>      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-zinc-800 border border-zinc-700 p-5 rounded-lg lg:col-span-3">          {book.chapters.length > 0 ? (
            /* Chapter Tabs Interface */
            <ChapterTabs 
              bookId={book.id} 
              className="h-full" 
              initialActiveChapter={initialChapter || undefined}
            />
          ) : (
            /* No chapters placeholder */
            <div className="flex flex-col items-center justify-center h-64 text-center">
              <div className="mb-4">
                <svg className="h-16 w-16 text-zinc-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                <h3 className="text-xl font-medium text-zinc-300 mb-2">No chapters yet</h3>
                <p className="text-zinc-400 text-sm max-w-md">
                  Complete your book summary and generate a Table of Contents to start writing chapters.
                </p>
              </div>
              {book?.summary && book.summary.length >= 30 ? (
                <Link href={`./generate-toc`}>
                  <button className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md">
                    Generate Table of Contents
                  </button>
                </Link>
              ) : (
                <Link href={`./summary`}>
                  <button className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md">
                    Complete Book Summary
                  </button>
                </Link>
              )}
            </div>
          )}
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
            <button
              onClick={handleExportClick}
              className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md transition-all"
            >
              Export Book
            </button>
          </div>
        </div>
      </div>

      {/* Export Modals */}
      <ExportOptionsModal
        bookId={bookId}
        isOpen={showExportOptions}
        onOpenChange={setShowExportOptions}
        onExport={handleExport}
        bookTitle={book.title}
      />

      <ExportProgressModal
        isOpen={showExportProgress}
        status={exportStatus}
        progress={exportProgress}
        error={exportError}
        filename={exportFilename}
        onCancel={handleRetryExport}
        onClose={handleCloseExportProgress}
      />
    </div>
  );
}
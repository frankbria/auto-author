'use client';

import { useState, useEffect, use, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@/lib/auth-client';
import bookClient from '@/lib/api/bookClient';
import { toast } from 'sonner';
import { BookProject } from '@/components/BookCard';
import { LoadingStateManager } from '@/components/loading';
import { createProgressTracker } from '@/lib/loading';

type ExportFormat = {
  format: string;
  name: string;
  description: string;
  icon: string;
  extension: string;
  mime_type: string;
  available: boolean;
  options?: Record<string, any>;
};

type ChapterStatus = {
  id: string;
  title: string;
  status: string;
  word_count: number;
};

export default function ExportBookPage({ params }: { params: Promise<{ bookId: string }> }) {
  const { bookId } = use(params);
  const router = useRouter();
  const { data: session } = useSession();
  const [isLoading, setIsLoading] = useState(true);
  const [book, setBook] = useState<BookProject | null>(null);
  const [formats, setFormats] = useState<ExportFormat[]>([]);
  const [selectedFormat, setSelectedFormat] = useState<string>('');
  const [chapters, setChapters] = useState<ChapterStatus[]>([]);
  const [includeEmptyChapters, setIncludeEmptyChapters] = useState(false);
  const [pageSize, setPageSize] = useState<'letter' | 'A4'>('letter');
  const [isExporting, setIsExporting] = useState(false);
  const [exportComplete, setExportComplete] = useState(false);
  const [downloadBlob, setDownloadBlob] = useState<Blob | null>(null);

  // Progress tracking for export operations
  const getProgress = useMemo(() => {
    if (!isExporting) return null;
    const wordCount = chapters.reduce((sum, ch) => sum + ch.word_count, 0);
    const chapterCount = includeEmptyChapters ? chapters.length : chapters.filter(ch => ch.word_count > 0).length;
    return createProgressTracker(
      selectedFormat === 'pdf' ? 'export.pdf' : 'export.docx',
      { wordCount, chapterCount }
    );
  }, [isExporting, selectedFormat, chapters, includeEmptyChapters]);

  const exportProgress = getProgress ? getProgress() : { progress: 0, estimatedTimeRemaining: 0 };

  // Fetch book details and export options
  useEffect(() => {
    const fetchBookDetails = async () => {
      try {

        // Fetch book details
        const bookData = await bookClient.getBook(bookId);
        setBook(bookData);

        // Fetch export formats
        const exportData = await bookClient.getExportFormats(bookId);

        // Add icons to formats (since API doesn't provide them)
        const formatsWithIcons = exportData.formats.map(format => ({
          ...format,
          icon: format.format === 'pdf' ? '📄' : format.format === 'docx' ? '📝' : '📋'
        }));

        setFormats(formatsWithIcons);

        // Set default format to first available one
        const firstAvailable = formatsWithIcons.find(f => f.available);
        if (firstAvailable) {
          setSelectedFormat(firstAvailable.format);
        }

        // Fetch chapters metadata
        const chaptersData = await bookClient.getChaptersMetadata(bookId);
        const chaptersFormatted: ChapterStatus[] = chaptersData.chapters.map(ch => ({
          id: ch.id,
          title: ch.title,
          status: ch.status,
          word_count: ch.word_count
        }));

        setChapters(chaptersFormatted);

      } catch (error) {
        console.error('Error fetching book details:', error);
        toast.error('Failed to load export options. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };
      fetchBookDetails();
  }, [bookId, session]);

  const handleExport = async () => {

    if (!selectedFormat) {
      toast.error('Please select an export format');
      return;
    }

    setIsExporting(true);

    try {
      let blob: Blob;

      if (selectedFormat === 'pdf') {
        blob = await bookClient.exportPDF(bookId, {
          includeEmptyChapters,
          pageSize
        });
      } else if (selectedFormat === 'docx') {
        blob = await bookClient.exportDOCX(bookId, {
          includeEmptyChapters
        });
      } else {
        toast.error('This export format is not yet implemented');
        setIsExporting(false);
        return;
      }

      setDownloadBlob(blob);
      setExportComplete(true);
    } catch (error) {
      console.error('Error exporting book:', error);
      toast.error('Failed to export book. Please try again.');
      setIsExporting(false);
    }
  };

  const handleDownload = () => {
    if (!downloadBlob || !book) return;

    const format = formats.find(f => f.format === selectedFormat);
    const url = window.URL.createObjectURL(downloadBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${book.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}${format?.extension || ''}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    toast.success('Download started!');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'draft':
        return 'bg-amber-600';
      case 'edited':
        return 'bg-blue-600';
      case 'final':
        return 'bg-green-600';
      default:
        return 'bg-zinc-600';
    }
  };

  const getStatusText = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  if (isLoading) {
    return (
      <div className="container mx-auto flex-1 p-6 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
          <p className="text-zinc-400">Loading export options...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-zinc-100">Export Book</h1>
          <p className="text-zinc-400 mt-1">{book?.title || ''}</p>
        </div>

        <button
          onClick={() => router.back()}
          className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded-md"
        >
          Back to Book
        </button>
      </div>

      {exportComplete ? (
        // Export Complete View
        <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-8 text-center">
          <div className="w-16 h-16 mx-auto bg-green-900/30 rounded-full flex items-center justify-center mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-green-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-zinc-100 mb-2">Export Complete!</h2>
          <p className="text-zinc-400 mb-6">
            Your book has been successfully exported in {formats.find(f => f.format === selectedFormat)?.name} format.
          </p>

          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <button
              onClick={handleDownload}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md flex items-center justify-center"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
              Download File
            </button>
            <button
              onClick={() => {
                setExportComplete(false);
                setIsExporting(false);
                setDownloadBlob(null);
              }}
              className="px-6 py-3 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded-md"
            >
              Export Another Format
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Export Format Selection */}
          <div className="lg:col-span-2">
            <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold text-zinc-100 mb-4">1. Choose Export Format</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                {formats.map(format => (
                  <div
                    key={format.format}
                    className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                      selectedFormat === format.format
                        ? 'border-indigo-500 bg-indigo-900/20'
                        : 'border-zinc-700 hover:bg-zinc-700/50'
                    } ${!format.available ? 'opacity-50 cursor-not-allowed' : ''}`}
                    onClick={() => format.available && setSelectedFormat(format.format)}
                  >
                    <div className="flex items-center mb-2">
                      <span className="text-2xl mr-3">{format.icon}</span>
                      <div className="flex-1">
                        <h3 className="font-medium text-zinc-200">{format.name}</h3>
                        <p className="text-zinc-400 text-xs">{format.extension}</p>
                      </div>
                      <div className={`w-4 h-4 rounded-full ${selectedFormat === format.format ? 'bg-indigo-500' : 'bg-zinc-700'}`}></div>
                    </div>
                    <p className="text-zinc-400 text-sm">{format.description}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Export Options */}
            <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold text-zinc-100 mb-4">2. Export Options</h2>
              <div className="space-y-4">
                {selectedFormat === 'pdf' && (
                  <div className="space-y-4">
                    <div className="flex items-start">
                      <div className="mt-1">
                        <label className="inline-flex items-center cursor-pointer">
                          <div className="relative">
                            <input
                              type="checkbox"
                              className="sr-only peer"
                              checked={includeEmptyChapters}
                              onChange={() => setIncludeEmptyChapters(!includeEmptyChapters)}
                            />
                            <div className="w-10 h-5 bg-zinc-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-zinc-400 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-900 peer-checked:after:bg-indigo-500"></div>
                          </div>
                        </label>
                      </div>
                      <div className="ml-3">
                        <h3 className="font-medium text-zinc-200">Include Empty Chapters</h3>
                        <p className="text-zinc-400 text-sm">Export chapters that don't have content yet</p>
                      </div>
                    </div>

                    <div>
                      <h3 className="font-medium text-zinc-200 mb-2">Page Size</h3>
                      <div className="flex gap-4">
                        <label className="flex items-center">
                          <input
                            type="radio"
                            name="pageSize"
                            value="letter"
                            checked={pageSize === 'letter'}
                            onChange={() => setPageSize('letter')}
                            className="mr-2"
                          />
                          <span className="text-zinc-300">Letter (8.5" × 11")</span>
                        </label>
                        <label className="flex items-center">
                          <input
                            type="radio"
                            name="pageSize"
                            value="A4"
                            checked={pageSize === 'A4'}
                            onChange={() => setPageSize('A4')}
                            className="mr-2"
                          />
                          <span className="text-zinc-300">A4 (210mm × 297mm)</span>
                        </label>
                      </div>
                    </div>
                  </div>
                )}

                {selectedFormat === 'docx' && (
                  <div className="flex items-start">
                    <div className="mt-1">
                      <label className="inline-flex items-center cursor-pointer">
                        <div className="relative">
                          <input
                            type="checkbox"
                            className="sr-only peer"
                            checked={includeEmptyChapters}
                            onChange={() => setIncludeEmptyChapters(!includeEmptyChapters)}
                          />
                          <div className="w-10 h-5 bg-zinc-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-zinc-400 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-900 peer-checked:after:bg-indigo-500"></div>
                        </div>
                      </label>
                    </div>
                    <div className="ml-3">
                      <h3 className="font-medium text-zinc-200">Include Empty Chapters</h3>
                      <p className="text-zinc-400 text-sm">Export chapters that don't have content yet</p>
                    </div>
                  </div>
                )}

                {!selectedFormat && (
                  <p className="text-zinc-400 text-center py-4">Select a format to see available options</p>
                )}
              </div>
            </div>

            {/* Chapter Summary */}
            <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-zinc-100 mb-4">3. Chapter Information</h2>
              <div className="space-y-3">
                <div className="text-zinc-300">
                  <span className="text-zinc-400">Total chapters:</span> {chapters.length}
                </div>
                <div className="text-zinc-300">
                  <span className="text-zinc-400">Chapters with content:</span> {chapters.filter(ch => ch.word_count > 0).length}
                </div>
                <div className="text-zinc-300">
                  <span className="text-zinc-400">Total word count:</span> {chapters.reduce((sum, ch) => sum + ch.word_count, 0).toLocaleString()}
                </div>
              </div>

              {chapters.length === 0 && (
                <div className="text-center py-6 mt-4">
                  <p className="text-zinc-400">No chapters found in this book.</p>
                </div>
              )}

              {chapters.length > 0 && chapters.filter(ch => ch.word_count === 0).length > 0 && !includeEmptyChapters && (
                <div className="mt-4 p-3 bg-amber-900/20 border border-amber-700/50 rounded-md">
                  <p className="text-amber-300 text-sm">
                    Note: {chapters.filter(ch => ch.word_count === 0).length} empty chapter(s) will be excluded from export. Enable "Include Empty Chapters" to include them.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Export Summary */}
          <div className="lg:col-span-1">
            <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6 sticky top-24">
              <h2 className="text-xl font-semibold text-zinc-100 mb-4">Export Summary</h2>

              <div className="space-y-4">
                <div>
                  <h3 className="text-zinc-400 text-sm">Book</h3>
                  <p className="text-zinc-200">{book?.title || ''}</p>
                </div>

                <div>
                  <h3 className="text-zinc-400 text-sm">Format</h3>
                  <p className="text-zinc-200">
                    {formats.find(f => f.format === selectedFormat)?.name || 'Not selected'}
                  </p>
                </div>

                <div>
                  <h3 className="text-zinc-400 text-sm">Options</h3>
                  <div className="space-y-1 mt-1">
                    {selectedFormat === 'pdf' && (
                      <>
                        <div className="text-zinc-300 text-sm flex items-center">
                          <div className="w-1 h-1 rounded-full bg-indigo-500 mr-2"></div>
                          Page size: {pageSize === 'letter' ? 'Letter' : 'A4'}
                        </div>
                        {includeEmptyChapters && (
                          <div className="text-zinc-300 text-sm flex items-center">
                            <div className="w-1 h-1 rounded-full bg-indigo-500 mr-2"></div>
                            Include empty chapters
                          </div>
                        )}
                      </>
                    )}
                    {selectedFormat === 'docx' && includeEmptyChapters && (
                      <div className="text-zinc-300 text-sm flex items-center">
                        <div className="w-1 h-1 rounded-full bg-indigo-500 mr-2"></div>
                        Include empty chapters
                      </div>
                    )}
                    {!selectedFormat && (
                      <p className="text-zinc-500 text-sm">No format selected</p>
                    )}
                  </div>
                </div>

                <div>
                  <h3 className="text-zinc-400 text-sm">Export Details</h3>
                  <div className="space-y-1 mt-1">
                    <p className="text-zinc-300 text-sm">
                      {includeEmptyChapters ? chapters.length : chapters.filter(ch => ch.word_count > 0).length} chapters
                    </p>
                    <p className="text-zinc-300 text-sm">
                      {chapters.reduce((sum, ch) => sum + ch.word_count, 0).toLocaleString()} words
                    </p>
                  </div>
                </div>
              </div>

              {isExporting ? (
                <div className="mt-6">
                  <LoadingStateManager
                    isLoading={true}
                    operation={`Generating ${selectedFormat.toUpperCase()}`}
                    progress={exportProgress.progress}
                    estimatedTime={exportProgress.estimatedTimeRemaining}
                    message={`Processing ${includeEmptyChapters ? chapters.length : chapters.filter(ch => ch.word_count > 0).length} chapters...`}
                    inline
                  />
                </div>
              ) : (
                <div className="mt-6">
                  <button
                    onClick={handleExport}
                    disabled={!selectedFormat || chapters.length === 0 || (chapters.filter(ch => ch.word_count > 0).length === 0 && !includeEmptyChapters)}
                    className="w-full px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Export Book
                  </button>

                  {chapters.length === 0 && (
                    <p className="text-amber-400 text-xs mt-2">
                      This book has no chapters to export.
                    </p>
                  )}
                  {chapters.length > 0 && chapters.filter(ch => ch.word_count > 0).length === 0 && !includeEmptyChapters && (
                    <p className="text-amber-400 text-xs mt-2">
                      All chapters are empty. Enable "Include Empty Chapters" to export.
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

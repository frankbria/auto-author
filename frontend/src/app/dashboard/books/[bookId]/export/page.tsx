'use client';

import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';

type ExportFormat = {
  id: string;
  name: string;
  description: string;
  icon: string;
  fileExtension: string;
};

type ExportOption = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
};

type ChapterStatus = {
  id: string;
  title: string;
  status: 'draft' | 'edited' | 'final';
};

export default function ExportBookPage({ params }: { params: Promise<{ bookId: string }> }) {
  const { bookId } = use(params);
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [bookTitle, setBookTitle] = useState('');
  const [formats, setFormats] = useState<ExportFormat[]>([]);
  const [selectedFormat, setSelectedFormat] = useState<string>('');
  const [exportOptions, setExportOptions] = useState<ExportOption[]>([]);
  const [chapters, setChapters] = useState<ChapterStatus[]>([]);
  const [selectedChapters, setSelectedChapters] = useState<string[]>([]);
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [exportComplete, setExportComplete] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState('');
  
  // Fetch book details and export options
  useEffect(() => {
    const fetchBookDetails = async () => {
      try {        // In a real app, this would call your API
        // const response = await bookClient.getBookDetails(bookId);
        // const data = await response.json();
        
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Sample book title
        setBookTitle('The Complete Guide to Machine Learning');
        
        // Sample export formats
        const formatsData: ExportFormat[] = [
          {
            id: 'pdf',
            name: 'PDF',
            description: 'Portable Document Format with fixed layout',
            icon: '📄',
            fileExtension: '.pdf'
          },
          {
            id: 'epub',
            name: 'EPUB',
            description: 'Electronic publication for e-readers',
            icon: '📱',
            fileExtension: '.epub'
          },
          {
            id: 'docx',
            name: 'Word Document',
            description: 'Microsoft Word format for further editing',
            icon: '📝',
            fileExtension: '.docx'
          },
          {
            id: 'html',
            name: 'HTML',
            description: 'Web format for online publishing',
            icon: '🌐',
            fileExtension: '.html'
          },
          {
            id: 'markdown',
            name: 'Markdown',
            description: 'Plain text format with simple formatting',
            icon: '📋',
            fileExtension: '.md'
          }
        ];
        
        // Sample export options
        const optionsData: ExportOption[] = [
          {
            id: 'cover',
            name: 'Include Cover Page',
            description: 'Add a cover page with book title and author',
            enabled: true
          },
          {
            id: 'toc',
            name: 'Include Table of Contents',
            description: 'Add a structured table of contents',
            enabled: true
          },
          {
            id: 'page-numbers',
            name: 'Include Page Numbers',
            description: 'Add page numbers to the document',
            enabled: true
          },
          {
            id: 'headers',
            name: 'Include Headers',
            description: 'Add chapter titles as page headers',
            enabled: false
          },
          {
            id: 'footnotes',
            name: 'Convert Links to Footnotes',
            description: 'Convert hyperlinks to numbered footnotes',
            enabled: false
          }
        ];
        
        // Sample chapters
        const chaptersData: ChapterStatus[] = [
          {
            id: 'ch1',
            title: 'Introduction to Machine Learning',
            status: 'final'
          },
          {
            id: 'ch2',
            title: 'Types of Learning Algorithms',
            status: 'edited'
          },
          {
            id: 'ch3',
            title: 'Practical Applications',
            status: 'draft'
          },
          {
            id: 'ch4',
            title: 'Feature Engineering',
            status: 'draft'
          },
          {
            id: 'ch5',
            title: 'Model Evaluation',
            status: 'draft'
          }
        ];
        
        setFormats(formatsData);
        setSelectedFormat('pdf');  // Default selected format
        setExportOptions(optionsData);
        setChapters(chaptersData);
        
        // Select all chapters by default
        setSelectedChapters(chaptersData.map(chapter => chapter.id));
        
      } catch (error) {
        console.error('Error fetching book details:', error);
      } finally {
        setIsLoading(false);
      }
    };
      fetchBookDetails();
  }, [bookId]);
  
  const toggleOption = (optionId: string) => {
    setExportOptions(prev => 
      prev.map(option => 
        option.id === optionId
          ? { ...option, enabled: !option.enabled }
          : option
      )
    );
  };
  
  const toggleChapter = (chapterId: string) => {
    setSelectedChapters(prev => 
      prev.includes(chapterId)
        ? prev.filter(id => id !== chapterId)
        : [...prev, chapterId]
    );
  };
  
  const toggleAllChapters = () => {
    if (selectedChapters.length === chapters.length) {
      setSelectedChapters([]);
    } else {
      setSelectedChapters(chapters.map(chapter => chapter.id));
    }
  };
  
  const handleExport = async () => {
    if (selectedChapters.length === 0) {
      // Show error or notification that at least one chapter must be selected
      return;
    }
    
    setIsExporting(true);
    setExportProgress(0);
    
    // Simulate export process with progress updates
    const interval = setInterval(() => {
      setExportProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          return 100;
        }
        return prev + 10;
      });
    }, 300);
    
    try {
      // In a real app, this would call your API to generate the export
      // const response = await bookClient.exportBook({
      //   bookId: params.bookId,
      //   formatId: selectedFormat,
      //   options: exportOptions.filter(o => o.enabled).map(o => o.id),
      //   chapterIds: selectedChapters
      // });
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      // Clear the progress interval
      clearInterval(interval);
      setExportProgress(100);
        // Set the download URL (in a real app this would come from the API)
      const format = formats.find(f => f.id === selectedFormat);
      setDownloadUrl(`/api/books/${bookId}/exports/download-${Date.now()}${format?.fileExtension || ''}`);
      
      // Mark export as complete
      setExportComplete(true);
    } catch (error) {
      console.error('Error exporting book:', error);
      clearInterval(interval);
      setIsExporting(false);
    }
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
          <p className="text-zinc-400 mt-1">{bookTitle}</p>
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
            Your book has been successfully exported in {formats.find(f => f.id === selectedFormat)?.name} format.
          </p>
          
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <a 
              href={downloadUrl} 
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md flex items-center justify-center"
              download={`${bookTitle.replace(/\s+/g, '-').toLowerCase()}${formats.find(f => f.id === selectedFormat)?.fileExtension}`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
              Download File
            </a>
            <button 
              onClick={() => {
                setExportComplete(false);
                setIsExporting(false);
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
                    key={format.id}
                    className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                      selectedFormat === format.id
                        ? 'border-indigo-500 bg-indigo-900/20'
                        : 'border-zinc-700 hover:bg-zinc-700/50'
                    }`}
                    onClick={() => setSelectedFormat(format.id)}
                  >
                    <div className="flex items-center mb-2">
                      <span className="text-2xl mr-3">{format.icon}</span>
                      <div className="flex-1">
                        <h3 className="font-medium text-zinc-200">{format.name}</h3>
                        <p className="text-zinc-400 text-xs">{format.fileExtension}</p>
                      </div>
                      <div className={`w-4 h-4 rounded-full ${selectedFormat === format.id ? 'bg-indigo-500' : 'bg-zinc-700'}`}></div>
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
                {exportOptions.map(option => (
                  <div 
                    key={option.id}
                    className="flex items-start"
                  >
                    <div className="mt-1">
                      <label className="inline-flex items-center cursor-pointer">
                        <div className="relative">
                          <input 
                            type="checkbox" 
                            className="sr-only peer"
                            checked={option.enabled}
                            onChange={() => toggleOption(option.id)}
                          />
                          <div className="w-10 h-5 bg-zinc-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-zinc-400 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-900 peer-checked:after:bg-indigo-500"></div>
                        </div>
                      </label>
                    </div>
                    <div className="ml-3">
                      <h3 className="font-medium text-zinc-200">{option.name}</h3>
                      <p className="text-zinc-400 text-sm">{option.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Chapter Selection */}
            <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-zinc-100">3. Select Chapters</h2>
                <button 
                  onClick={toggleAllChapters}
                  className="text-indigo-400 hover:text-indigo-300 text-sm"
                >
                  {selectedChapters.length === chapters.length ? 'Deselect All' : 'Select All'}
                </button>
              </div>
              
              <div className="space-y-3">
                {chapters.map(chapter => (
                  <div 
                    key={chapter.id}
                    className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                      selectedChapters.includes(chapter.id)
                        ? 'border-indigo-500 bg-indigo-900/20'
                        : 'border-zinc-700 hover:bg-zinc-700/50'
                    }`}
                    onClick={() => toggleChapter(chapter.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <div className={`w-3 h-3 rounded-full ${getStatusColor(chapter.status)} mr-3`}></div>
                        <div>
                          <h3 className="font-medium text-zinc-200">{chapter.title}</h3>
                          <p className="text-zinc-400 text-xs">{getStatusText(chapter.status)}</p>
                        </div>
                      </div>
                      <div>
                        <div className={`w-5 h-5 rounded border ${
                          selectedChapters.includes(chapter.id)
                            ? 'bg-indigo-500 border-indigo-500'
                            : 'bg-transparent border-zinc-600'
                        } flex items-center justify-center`}>
                          {selectedChapters.includes(chapter.id) && (
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              {chapters.length === 0 && (
                <div className="text-center py-6">
                  <p className="text-zinc-400">No chapters found in this book.</p>
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
                  <p className="text-zinc-200">{bookTitle}</p>
                </div>
                
                <div>
                  <h3 className="text-zinc-400 text-sm">Format</h3>
                  <p className="text-zinc-200">
                    {formats.find(f => f.id === selectedFormat)?.name || 'Not selected'}
                  </p>
                </div>
                
                <div>
                  <h3 className="text-zinc-400 text-sm">Options</h3>
                  <div className="space-y-1 mt-1">
                    {exportOptions.filter(o => o.enabled).length > 0 ? (
                      exportOptions
                        .filter(o => o.enabled)
                        .map(option => (
                          <div key={option.id} className="text-zinc-300 text-sm flex items-center">
                            <div className="w-1 h-1 rounded-full bg-indigo-500 mr-2"></div>
                            {option.name}
                          </div>
                        ))
                    ) : (
                      <p className="text-zinc-500 text-sm">No options selected</p>
                    )}
                  </div>
                </div>
                
                <div>
                  <h3 className="text-zinc-400 text-sm">Chapters</h3>
                  <p className="text-zinc-200">
                    {selectedChapters.length} of {chapters.length} selected
                  </p>
                </div>
              </div>
              
              {isExporting ? (
                <div className="mt-6">
                  <div className="flex justify-between text-sm text-zinc-400 mb-2">
                    <span>Exporting...</span>
                    <span>{exportProgress}%</span>
                  </div>
                  <div className="w-full bg-zinc-700 rounded-full h-2">
                    <div 
                      className="bg-indigo-600 h-2 rounded-full transition-all duration-300" 
                      style={{ width: `${exportProgress}%` }}
                    ></div>
                  </div>
                </div>
              ) : (
                <div className="mt-6">
                  <button
                    onClick={handleExport}
                    disabled={!selectedFormat || selectedChapters.length === 0}
                    className="w-full px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Export Book
                  </button>
                  
                  {selectedChapters.length === 0 && (
                    <p className="text-amber-400 text-xs mt-2">
                      Please select at least one chapter to export.
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

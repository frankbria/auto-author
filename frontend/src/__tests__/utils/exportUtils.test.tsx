/**
 * @jest-environment jsdom
 */
import { toast } from 'sonner';
import bookClient from '@/lib/api/bookClient';

// Mock dependencies
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    setAuthToken: jest.fn(),
    exportPDF: jest.fn(),
    exportDOCX: jest.fn(),
    getExportFormats: jest.fn(),
    getBook: jest.fn(),
    getChaptersMetadata: jest.fn(),
  },
}));

// Export utility functions (extracted from export page logic)
const loadExportData = async (
  bookId: string,
  getToken: () => Promise<string>
) => {
  const token = await getToken();
  bookClient.setAuthToken(token);
  
  const [book, exportFormats, chaptersMetadata] = await Promise.all([
    bookClient.getBook(bookId),
    bookClient.getExportFormats(bookId),
    bookClient.getChaptersMetadata(bookId),
  ]);
  
  return { book, exportFormats, chaptersMetadata };
};

const exportBook = async (
  bookId: string,
  bookTitle: string,
  format: string,
  options: any,
  getToken: () => Promise<string>,
  setIsExporting: (value: boolean) => void
) => {
  setIsExporting(true);
  
  try {
    const token = await getToken();
    bookClient.setAuthToken(token);
    
    let blob;
    if (format === 'pdf') {
      blob = await bookClient.exportPDF(bookId, options);
    } else if (format === 'docx') {
      blob = await bookClient.exportDOCX(bookId, options);
    } else {
      throw new Error(`Unsupported format: ${format}`);
    }
    
    // Create download link
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${bookTitle.replace(/[^a-zA-Z0-9]/g, '_')}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success(`${format.toUpperCase()} exported successfully!`);
    return true;
  } catch (error) {
    console.error('Export failed:', error);
    if (error instanceof Error && error.message.includes('Unsupported format')) {
      toast.error(`${format.toUpperCase()} format is not supported.`);
    } else {
      toast.error('Export failed. Please try again.');
    }
    return false;
  } finally {
    setIsExporting(false);
  }
};

describe('Export Utils', () => {
  const mockGetToken = jest.fn();
  const mockSetIsExporting = jest.fn();
  
  const mockBookData = {
    id: 'test-book-id',
    title: 'Test Book for Export',
    description: 'Test description',
  };

  const mockExportFormats = {
    formats: [
      {
        format: 'pdf',
        name: 'PDF',
        description: 'Portable Document Format',
        available: true,
      },
      {
        format: 'docx',
        name: 'Word Document',
        description: 'Microsoft Word format',
        available: true,
      },
      {
        format: 'epub',
        name: 'EPUB',
        description: 'Electronic publication',
        available: false,
      },
    ],
    book_stats: {
      total_chapters: 5,
      chapters_with_content: 3,
      total_word_count: 15000,
      estimated_pages: 60,
    },
  };

  const mockChaptersMetadata = {
    book_id: 'test-book-id',
    chapters: [
      {
        id: 'ch1',
        title: 'Introduction',
        description: 'Intro chapter',
        level: 1,
        order: 1,
        status: 'completed',
        word_count: 5000,
      },
      {
        id: 'ch2',
        title: 'Chapter 2',
        description: 'Second chapter',
        level: 1,
        order: 2,
        status: 'draft',
        word_count: 3000,
      },
    ],
    total_chapters: 2,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock URL methods
    global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = jest.fn();
    
    // Mock document methods
    const originalCreateElement = document.createElement;
    document.createElement = jest.fn((tagName) => {
      if (tagName === 'a') {
        return {
          click: jest.fn(),
          href: '',
          download: '',
          style: {},
        } as any;
      }
      return originalCreateElement.call(document, tagName);
    });
    
    document.body.appendChild = jest.fn();
    document.body.removeChild = jest.fn();
    
    // Setup default mocks
    mockGetToken.mockResolvedValue('test-token');
    (bookClient.getBook as jest.Mock).mockResolvedValue(mockBookData);
    (bookClient.getExportFormats as jest.Mock).mockResolvedValue(mockExportFormats);
    (bookClient.getChaptersMetadata as jest.Mock).mockResolvedValue(mockChaptersMetadata);
  });

  describe('loadExportData', () => {
    it('should load all export data successfully', async () => {
      const result = await loadExportData('test-book-id', mockGetToken);
      
      expect(bookClient.setAuthToken).toHaveBeenCalledWith('test-token');
      expect(bookClient.getBook).toHaveBeenCalledWith('test-book-id');
      expect(bookClient.getExportFormats).toHaveBeenCalledWith('test-book-id');
      expect(bookClient.getChaptersMetadata).toHaveBeenCalledWith('test-book-id');
      
      expect(result.book).toEqual(mockBookData);
      expect(result.exportFormats).toEqual(mockExportFormats);
      expect(result.chaptersMetadata).toEqual(mockChaptersMetadata);
    });

    it('should handle API errors when loading data', async () => {
      (bookClient.getBook as jest.Mock).mockRejectedValue(new Error('API Error'));
      
      await expect(loadExportData('test-book-id', mockGetToken)).rejects.toThrow('API Error');
      
      expect(bookClient.setAuthToken).toHaveBeenCalledWith('test-token');
    });

    it('should handle authentication errors', async () => {
      mockGetToken.mockRejectedValue(new Error('Auth failed'));
      
      await expect(loadExportData('test-book-id', mockGetToken)).rejects.toThrow('Auth failed');
    });
  });

  describe('exportBook', () => {
    it('should export PDF successfully', async () => {
      const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });
      (bookClient.exportPDF as jest.Mock).mockResolvedValue(mockBlob);
      
      const result = await exportBook(
        'test-book-id',
        'Test Book',
        'pdf',
        { includeEmptyChapters: false },
        mockGetToken,
        mockSetIsExporting
      );
      
      expect(result).toBe(true);
      expect(mockSetIsExporting).toHaveBeenCalledWith(true);
      expect(bookClient.setAuthToken).toHaveBeenCalledWith('test-token');
      expect(bookClient.exportPDF).toHaveBeenCalledWith('test-book-id', {
        includeEmptyChapters: false,
      });
      expect(toast.success).toHaveBeenCalledWith('PDF exported successfully!');
      expect(mockSetIsExporting).toHaveBeenCalledWith(false);
    });

    it('should export DOCX successfully', async () => {
      const mockBlob = new Blob(['DOCX content'], { 
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
      });
      (bookClient.exportDOCX as jest.Mock).mockResolvedValue(mockBlob);
      
      const result = await exportBook(
        'test-book-id',
        'Test Book',
        'docx',
        { includeEmptyChapters: true },
        mockGetToken,
        mockSetIsExporting
      );
      
      expect(result).toBe(true);
      expect(bookClient.exportDOCX).toHaveBeenCalledWith('test-book-id', {
        includeEmptyChapters: true,
      });
      expect(toast.success).toHaveBeenCalledWith('DOCX exported successfully!');
    });

    it('should create correct download filename for different formats', async () => {
      const mockBlob = new Blob(['content']);
      (bookClient.exportPDF as jest.Mock).mockResolvedValue(mockBlob);
      
      const mockAnchor = {
        click: jest.fn(),
        href: '',
        download: '',
        style: {},
      };
      
      document.createElement = jest.fn(() => mockAnchor as any);
      
      await exportBook(
        'test-book-id',
        'My Complex Book: Title! (2024)',
        'pdf',
        {},
        mockGetToken,
        mockSetIsExporting
      );
      
      expect(mockAnchor.download).toBe('My_Complex_Book__Title___2024_.pdf');
    });

    it('should handle unsupported format error', async () => {
      const result = await exportBook(
        'test-book-id',
        'Test Book',
        'epub',
        {},
        mockGetToken,
        mockSetIsExporting
      );
      
      expect(result).toBe(false);
      expect(toast.error).toHaveBeenCalledWith('EPUB format is not supported.');
      expect(mockSetIsExporting).toHaveBeenCalledWith(false);
    });

    it('should handle export API errors', async () => {
      (bookClient.exportPDF as jest.Mock).mockRejectedValue(new Error('Export failed'));
      const consoleError = jest.spyOn(console, 'error').mockImplementation();
      
      const result = await exportBook(
        'test-book-id',
        'Test Book',
        'pdf',
        {},
        mockGetToken,
        mockSetIsExporting
      );
      
      expect(result).toBe(false);
      expect(consoleError).toHaveBeenCalledWith('Export failed:', expect.any(Error));
      expect(toast.error).toHaveBeenCalledWith('Export failed. Please try again.');
      expect(mockSetIsExporting).toHaveBeenCalledWith(false);
      
      consoleError.mockRestore();
    });

    it('should handle authentication errors during export', async () => {
      mockGetToken.mockRejectedValue(new Error('Auth failed'));
      const consoleError = jest.spyOn(console, 'error').mockImplementation();
      
      const result = await exportBook(
        'test-book-id',
        'Test Book',
        'pdf',
        {},
        mockGetToken,
        mockSetIsExporting
      );
      
      expect(result).toBe(false);
      expect(consoleError).toHaveBeenCalledWith('Export failed:', expect.any(Error));
      expect(mockSetIsExporting).toHaveBeenCalledWith(false);
      
      consoleError.mockRestore();
    });

    it('should properly clean up download link after successful export', async () => {
      const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });
      (bookClient.exportPDF as jest.Mock).mockResolvedValue(mockBlob);
      
      const mockAnchor = {
        click: jest.fn(),
        href: '',
        download: '',
        style: {},
      };
      
      document.createElement = jest.fn(() => mockAnchor as any);
      
      await exportBook(
        'test-book-id',
        'Test Book',
        'pdf',
        {},
        mockGetToken,
        mockSetIsExporting
      );
      
      expect(global.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
      expect(mockAnchor.click).toHaveBeenCalled();
      expect(document.body.appendChild).toHaveBeenCalledWith(mockAnchor);
      expect(document.body.removeChild).toHaveBeenCalledWith(mockAnchor);
      expect(global.URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
    });
  });
});
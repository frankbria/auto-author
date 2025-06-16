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
  },
}));

// PDF Export utility function (extracted from book detail page logic)
const exportPDFUtility = async (
  bookId: string,
  bookTitle: string,
  getToken: () => Promise<string>,
  setIsExporting: (value: boolean) => void
) => {
  setIsExporting(true);
  
  try {
    const token = await getToken();
    bookClient.setAuthToken(token);
    
    const blob = await bookClient.exportPDF(bookId, {
      includeEmptyChapters: false,
      pageSize: 'letter',
    });
    
    // Create download link
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${bookTitle.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success('PDF exported successfully!');
  } catch (error) {
    console.error('PDF export failed:', error);
    toast.error('Failed to export PDF. Please try again.');
  } finally {
    setIsExporting(false);
  }
};

describe('PDF Export Utility', () => {
  const mockGetToken = jest.fn();
  const mockSetIsExporting = jest.fn();
  
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
  });

  it('should successfully export PDF with correct parameters', async () => {
    const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });
    (bookClient.exportPDF as jest.Mock).mockResolvedValue(mockBlob);
    
    await exportPDFUtility('test-book-id', 'Test Book', mockGetToken, mockSetIsExporting);
    
    expect(mockSetIsExporting).toHaveBeenCalledWith(true);
    expect(bookClient.setAuthToken).toHaveBeenCalledWith('test-token');
    expect(bookClient.exportPDF).toHaveBeenCalledWith('test-book-id', {
      includeEmptyChapters: false,
      pageSize: 'letter',
    });
    expect(mockSetIsExporting).toHaveBeenCalledWith(false);
  });

  it('should create download link with correct filename', async () => {
    const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });
    (bookClient.exportPDF as jest.Mock).mockResolvedValue(mockBlob);
    
    const mockAnchor = {
      click: jest.fn(),
      href: '',
      download: '',
      style: {},
    };
    
    document.createElement = jest.fn(() => mockAnchor as any);
    
    await exportPDFUtility('test-book-id', 'My Test Book!', mockGetToken, mockSetIsExporting);
    
    expect(global.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
    expect(mockAnchor.download).toBe('My_Test_Book_.pdf');
    expect(mockAnchor.click).toHaveBeenCalled();
    expect(document.body.appendChild).toHaveBeenCalledWith(mockAnchor);
    expect(document.body.removeChild).toHaveBeenCalledWith(mockAnchor);
    expect(global.URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });

  it('should show success toast after successful export', async () => {
    const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });
    (bookClient.exportPDF as jest.Mock).mockResolvedValue(mockBlob);
    
    await exportPDFUtility('test-book-id', 'Test Book', mockGetToken, mockSetIsExporting);
    
    expect(toast.success).toHaveBeenCalledWith('PDF exported successfully!');
  });

  it('should handle authentication token retrieval errors', async () => {
    mockGetToken.mockRejectedValue(new Error('Auth failed'));
    const consoleError = jest.spyOn(console, 'error').mockImplementation();
    
    await exportPDFUtility('test-book-id', 'Test Book', mockGetToken, mockSetIsExporting);
    
    expect(mockSetIsExporting).toHaveBeenCalledWith(true);
    expect(mockSetIsExporting).toHaveBeenCalledWith(false);
    expect(consoleError).toHaveBeenCalledWith('PDF export failed:', expect.any(Error));
    expect(toast.error).toHaveBeenCalledWith('Failed to export PDF. Please try again.');
    
    consoleError.mockRestore();
  });

  it('should handle PDF export API errors', async () => {
    (bookClient.exportPDF as jest.Mock).mockRejectedValue(new Error('Export API failed'));
    const consoleError = jest.spyOn(console, 'error').mockImplementation();
    
    await exportPDFUtility('test-book-id', 'Test Book', mockGetToken, mockSetIsExporting);
    
    expect(bookClient.setAuthToken).toHaveBeenCalledWith('test-token');
    expect(bookClient.exportPDF).toHaveBeenCalledWith('test-book-id', {
      includeEmptyChapters: false,
      pageSize: 'letter',
    });
    expect(consoleError).toHaveBeenCalledWith('PDF export failed:', expect.any(Error));
    expect(toast.error).toHaveBeenCalledWith('Failed to export PDF. Please try again.');
    expect(mockSetIsExporting).toHaveBeenCalledWith(false);
    
    consoleError.mockRestore();
  });

  it('should sanitize book titles with special characters', async () => {
    const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });
    (bookClient.exportPDF as jest.Mock).mockResolvedValue(mockBlob);
    
    const mockAnchor = {
      click: jest.fn(),
      href: '',
      download: '',
      style: {},
    };
    
    document.createElement = jest.fn(() => mockAnchor as any);
    
    await exportPDFUtility(
      'test-book-id', 
      'My Book: A Story! (2024) [Draft] & More...', 
      mockGetToken, 
      mockSetIsExporting
    );
    
    expect(mockAnchor.download).toBe('My_Book__A_Story___2024___Draft____More___.pdf');
  });

  it('should always reset loading state even if download fails', async () => {
    const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });
    (bookClient.exportPDF as jest.Mock).mockResolvedValue(mockBlob);
    
    // Make URL.createObjectURL throw to simulate download failure
    global.URL.createObjectURL = jest.fn(() => {
      throw new Error('Blob creation failed');
    });
    
    const consoleError = jest.spyOn(console, 'error').mockImplementation();
    
    await exportPDFUtility('test-book-id', 'Test Book', mockGetToken, mockSetIsExporting);
    
    expect(mockSetIsExporting).toHaveBeenCalledWith(true);
    expect(mockSetIsExporting).toHaveBeenCalledWith(false);
    expect(consoleError).toHaveBeenCalledWith('PDF export failed:', expect.any(Error));
    
    consoleError.mockRestore();
  });
});
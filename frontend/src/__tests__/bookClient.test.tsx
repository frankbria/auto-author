import { bookClient } from '@/lib/api/bookClient';

// Mock fetch globally
global.fetch = jest.fn();

describe('BookClient', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset auth token
    bookClient.setAuthToken('test-token');
  });

  describe('Chapter Content Methods', () => {
    it('should get chapter content with metadata', async () => {
      const mockResponse = {
        book_id: 'book123',
        chapter_id: 'chapter456',
        title: 'Test Chapter',
        content: '<p>Test content</p>',
        success: true,
        metadata: {
          status: 'draft',
          word_count: 100,
          estimated_reading_time: 1,
          last_modified: '2025-01-01T00:00:00Z',
          is_active_tab: true,
          has_subchapters: false,
          subchapter_count: 0,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.getChapterContent('book123', 'chapter456');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/chapter456/content?include_metadata=true',
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should get chapter content without metadata', async () => {
      const mockResponse = {
        book_id: 'book123',
        chapter_id: 'chapter456',
        title: 'Test Chapter',
        content: '<p>Test content</p>',
        success: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.getChapterContent('book123', 'chapter456', false);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/chapter456/content?include_metadata=false',
        expect.any(Object)
      );

      expect(result).toEqual(mockResponse);
    });

    it('should save chapter content', async () => {
      const mockResponse = {
        book_id: 'book123',
        chapter_id: 'chapter456',
        content: '<p>Updated content</p>',
        metadata: {
          word_count: 150,
          estimated_reading_time: 1,
          last_modified: '2025-01-01T00:00:00Z',
          status: 'in-progress',
        },
        success: true,
        message: 'Chapter content saved successfully',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.saveChapterContent(
        'book123',
        'chapter456',
        '<p>Updated content</p>'
      );

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/chapter456/content',
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: JSON.stringify({
            content: '<p>Updated content</p>',
            auto_update_metadata: true,
          }),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should save chapter content without metadata update', async () => {
      const mockResponse = {
        book_id: 'book123',
        chapter_id: 'chapter456',
        content: '<p>Updated content</p>',
        metadata: {
          word_count: 150,
          estimated_reading_time: 1,
          last_modified: '2025-01-01T00:00:00Z',
        },
        success: true,
        message: 'Chapter content saved successfully',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.saveChapterContent(
        'book123',
        'chapter456',
        '<p>Updated content</p>',
        false
      );

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/chapter456/content',
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: JSON.stringify({
            content: '<p>Updated content</p>',
            auto_update_metadata: false,
          }),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle error when getting chapter content', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => 'Chapter not found',
      });

      await expect(
        bookClient.getChapterContent('book123', 'nonexistent')
      ).rejects.toThrow('Failed to get chapter content: 404 Chapter not found');
    });

    it('should handle error when saving chapter content', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 403,
        text: async () => 'Not authorized',
      });

      await expect(
        bookClient.saveChapterContent('book123', 'chapter456', '<p>Content</p>')
      ).rejects.toThrow('Failed to save chapter content: 403 Not authorized');
    });
  });
});
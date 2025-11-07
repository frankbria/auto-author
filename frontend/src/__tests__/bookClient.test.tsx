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
        'http://localhost:8000/api/v1/books/book123/chapters/chapter456/content?include_metadata=true&track_access=true',
        {
          method: 'GET',
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
        'http://localhost:8000/api/v1/books/book123/chapters/chapter456/content?include_metadata=false&track_access=true',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        }
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

  describe('Book Management Methods', () => {
    it('should get user books', async () => {
      const mockBooks = [
        {
          id: 'book1',
          title: 'Test Book 1',
          description: 'Test description 1',
          progress: 25,
          chapters: [],
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
        },
        {
          id: 'book2',
          title: 'Test Book 2',
          description: 'Test description 2',
          progress: 50,
          chapters: [],
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockBooks,
      });

      const result = await bookClient.getUserBooks();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books',
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        }
      );

      expect(result).toEqual(mockBooks);
    });

    it('should get a specific book', async () => {
      const mockBook = {
        id: 'book123',
        title: 'Test Book',
        description: 'Test description',
        progress: 75,
        chapters: [],
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockBook,
      });

      const result = await bookClient.getBook('book123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123',
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        }
      );

      expect(result).toEqual(mockBook);
    });

    it('should create a new book', async () => {
      const bookData = {
        title: 'New Test Book',
        description: 'A test book description',
        genre: 'Fiction',
        target_audience: 'Adults',
      };

      const mockResponse = {
        id: 'book456',
        ...bookData,
        progress: 0,
        chapters: [],
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.createBook(bookData);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: JSON.stringify(bookData),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should update a book', async () => {
      const updateData = {
        title: 'Updated Book Title',
        description: 'Updated description',
      };

      const mockResponse = {
        id: 'book123',
        ...updateData,
        progress: 50,
        chapters: [],
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T01:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.updateBook('book123', updateData);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123',
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: JSON.stringify(updateData),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should delete a book', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
      });

      await bookClient.deleteBook('book123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123',
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        }
      );
    });

    it('should handle error when getting user books', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: async () => 'Unauthorized',
      });

      await expect(bookClient.getUserBooks()).rejects.toThrow(
        'Failed to fetch books: 401'
      );
    });

    it('should handle error when getting specific book', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => 'Book not found',
      });

      await expect(bookClient.getBook('nonexistent')).rejects.toThrow(
        'Failed to fetch book: 404'
      );
    });

    it('should handle error when deleting book', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 403,
        text: async () => 'Not authorized',
      });

      await expect(bookClient.deleteBook('book123')).rejects.toThrow(
        'Failed to delete book: 403 Not authorized'
      );
    });
  });

  describe('Summary Management Methods', () => {
    it('should get book summary', async () => {
      const mockSummary = {
        summary: 'This is a test book summary',
        summary_history: [],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary,
      });

      const result = await bookClient.getBookSummary('book123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/summary',
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        }
      );

      expect(result).toEqual(mockSummary);
    });

    it('should save book summary', async () => {
      const mockResponse = {
        summary: 'Updated book summary',
        success: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.saveBookSummary('book123', 'Updated book summary');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/summary',
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: JSON.stringify({ summary: 'Updated book summary' }),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle error when getting book summary', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => 'Summary not found',
      });

      await expect(bookClient.getBookSummary('book123')).rejects.toThrow(
        'Failed to fetch book summary: 404 Summary not found'
      );
    });

    it('should handle error when saving book summary', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 400,
        text: async () => 'Invalid summary',
      });

      await expect(
        bookClient.saveBookSummary('book123', 'Invalid summary')
      ).rejects.toThrow('Failed to save book summary: 400 Invalid summary');
    });
  });

  describe('TOC Management Methods', () => {
    it('should get TOC', async () => {
      const mockToc = {
        toc: {
          id: 'toc123',
          chapters: [
            {
              id: 'ch1',
              title: 'Chapter 1',
              order: 1,
              subchapters: [],
            },
          ],
        },
        success: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockToc,
      });

      const result = await bookClient.getToc('book123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/toc',
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        }
      );

      expect(result).toEqual(mockToc);
    });

    it('should generate TOC from question responses', async () => {
      const questionResponses = [
        { question: 'What is the main topic?', answer: 'AI and automation' },
        { question: 'Who is the audience?', answer: 'Software developers' },
      ];

      const mockResponse = {
        toc: {
          id: 'toc123',
          chapters: [
            {
              id: 'ch1',
              title: 'Introduction to AI',
              order: 1,
              subchapters: [],
            },
          ],
        },
        generated_at: '2025-01-01T00:00:00Z',
        success: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.generateToc('book123', questionResponses);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/generate-toc',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: JSON.stringify({ question_responses: questionResponses }),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should update TOC', async () => {
      const tocData = {
        chapters: [
          {
            id: 'ch1',
            title: 'Updated Chapter 1',
            order: 1,
            subchapters: [],
          },
        ],
      };

      const mockResponse = {
        toc: tocData,
        updated_at: '2025-01-01T00:00:00Z',
        success: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.updateToc('book123', tocData);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/toc',
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: JSON.stringify({ toc: tocData }),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle error when getting TOC', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => 'TOC not found',
      });

      await expect(bookClient.getToc('book123')).rejects.toThrow(
        'Failed to get TOC: 404 TOC not found'
      );
    });

    it('should handle error when generating TOC', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Generation failed',
      });

      await expect(
        bookClient.generateToc('book123', [
          { question: 'Test?', answer: 'Test answer' },
        ])
      ).rejects.toThrow('Failed to generate TOC: 500 Generation failed');
    });
  });

  describe('Chapter Management Methods', () => {
    it('should create a new chapter', async () => {
      const mockChapter = {
        id: 'chapter123',
        title: 'New Chapter',
        content: '',
        order: 1,
        book_id: 'book123',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockChapter,
      });

      const result = await bookClient.createChapter('book123', {
        title: 'New Chapter',
        content: '',
        order: 1,
      });

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: JSON.stringify({
            title: 'New Chapter',
            content: '',
            order: 1,
          }),
        }
      );

      expect(result).toEqual(mockChapter);
    });

    it('should delete a chapter', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
      });

      await bookClient.deleteChapter('book123', 'chapter456');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/chapter456',
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        }
      );
    });

    it('should handle error when creating chapter', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 400,
        text: async () => 'Invalid chapter data',
      });

      await expect(
        bookClient.createChapter('book123', {
          title: 'Bad Chapter',
          content: '',
          order: 1,
        })
      ).rejects.toThrow('Failed to create chapter: 400 Invalid chapter data');
    });

    it('should handle error when deleting chapter', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => 'Chapter not found',
      });

      await expect(bookClient.deleteChapter('book123', 'nonexistent')).rejects.toThrow(
        'Failed to delete chapter: 404 Chapter not found'
      );
    });
  });

  describe('Authentication and Headers', () => {
    it('should set auth token', async () => {
      const newClient = new (bookClient.constructor as any)();
      newClient.setAuthToken('new-token');

      // Test that the token is used in requests
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      await newClient.getUserBooks();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer new-token',
          }),
        })
      );
    });

    it('should work without auth token', async () => {
      const newClient = new (bookClient.constructor as any)();
      
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      await newClient.getUserBooks();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.not.objectContaining({
            Authorization: expect.any(String),
          }),
        })
      );
    });
  });

  describe('Analysis Methods', () => {
    it('should check TOC readiness', async () => {
      const mockResponse = {
        book_id: 'book123',
        ready_for_toc: true,
        summary_length: 500,
        summary_quality_score: 0.85,
        requirements_met: ['length', 'clarity', 'structure'],
        requirements_missing: [],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.checkTocReadiness('book123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/toc-readiness',
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

    it('should analyze summary', async () => {
      const mockResponse = {
        book_id: 'book123',
        analysis: {
          is_ready_for_toc: true,
          confidence_score: 0.9,
          analysis: 'Summary is comprehensive and well-structured',
          suggestions: ['Consider adding more specific examples'],
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.analyzeSummary('book123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/analyze-summary',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle error when checking TOC readiness', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => 'Book not found',
      });

      await expect(bookClient.checkTocReadiness('book123')).rejects.toThrow(
        'Failed to check TOC readiness: 404 Book not found'
      );
    });

    it('should handle error when analyzing summary', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Analysis failed',
      });

      await expect(bookClient.analyzeSummary('book123')).rejects.toThrow(
        'Failed to analyze summary: 500 Analysis failed'
      );
    });
  });

  describe('Question Methods', () => {
    it('should generate questions', async () => {
      const mockResponse = {
        questions: [
          'What is the main theme?',
          'Who is the target audience?',
          'What are the key takeaways?',
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.generateQuestions('book123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/generate-questions',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should save question responses', async () => {
      const responses = [
        {
          id: 'resp1',
          question_id: 'q1',
          response_text: 'This is my answer',
          word_count: 4,
          quality_score: 0.9,
          response_status: 'completed' as any,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
          last_edited_at: '2025-01-01T00:00:00Z',
          metadata: {
            edit_history: [],
          },
        },
      ];

      const mockResponse = {
        book_id: 'book123',
        responses_saved: 1,
        answered_at: '2025-01-01T00:00:00Z',
        ready_for_toc_generation: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.saveQuestionResponses('book123', responses);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/question-responses',
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: JSON.stringify({ responses }),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should get question responses', async () => {
      const mockResponse = {
        responses: [
          {
            id: 'resp1',
            question_id: 'q1',
            response_text: 'This is my answer',
            word_count: 4,
          },
        ],
        answered_at: '2025-01-01T00:00:00Z',
        status: 'completed',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.getQuestionResponses('book123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/question-responses',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle error when generating questions', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Generation failed',
      });

      await expect(bookClient.generateQuestions('book123')).rejects.toThrow(
        'Failed to generate questions: 500 Generation failed'
      );
    });
  });

  describe('Chapter Metadata Methods', () => {
    it('should get chapters metadata', async () => {
      const mockResponse = {
        chapters: [
          {
            id: 'ch1',
            title: 'Chapter 1',
            level: 1,
            order: 1,
            status: 'draft',
            word_count: 500,
            estimated_reading_time: 2,
            last_modified: '2025-01-01T00:00:00Z',
          },
        ],
        total_chapters: 1,
        completion_stats: {
          draft: 1,
          in_progress: 0,
          completed: 0,
          published: 0,
        },
        last_active_chapter: 'ch1',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.getChaptersMetadata('book123', true);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/metadata?include_content_stats=true',
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

    it('should get chapters metadata without content stats', async () => {
      const mockResponse = {
        chapters: [],
        total_chapters: 0,
        completion_stats: {
          draft: 0,
          in_progress: 0,
          completed: 0,
          published: 0,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.getChaptersMetadata('book123', false);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/metadata?include_content_stats=false',
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

    it('should handle error when getting chapters metadata', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => 'Book not found',
      });

      await expect(bookClient.getChaptersMetadata('book123')).rejects.toThrow(
        'Failed to get chapters metadata: 404 Book not found'
      );
    });
  });

  describe('Chapter Status Methods', () => {
    it('should update chapter status', async () => {
      const mockResponse = {
        updated_chapters: ['ch1'],
        success: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.updateChapterStatus('book123', 'ch1', 'in-progress' as any);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/bulk-status',
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: JSON.stringify({
            chapter_ids: ['ch1'],
            status: 'in-progress',
            update_timestamp: true,
          }),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should update bulk chapter status', async () => {
      const mockResponse = {
        updated_chapters: ['ch1', 'ch2'],
        success: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.updateBulkChapterStatus(
        'book123',
        ['ch1', 'ch2'],
        'completed' as any
      );

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/bulk-status',
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: JSON.stringify({
            chapter_ids: ['ch1', 'ch2'],
            status: 'completed',
            update_timestamp: true,
          }),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle error when updating chapter status', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 400,
        text: async () => 'Invalid status',
      });

      await expect(
        bookClient.updateChapterStatus('book123', 'ch1', 'invalid' as any)
      ).rejects.toThrow('Failed to update chapter status: 400 Invalid status');
    });
  });

  describe('Tab State Methods', () => {
    it('should save tab state', async () => {
      const tabState = {
        active_chapter_id: 'ch1',
        open_tab_ids: ['ch1', 'ch2'],
        tab_order: ['ch1', 'ch2'],
      };

      const mockResponse = {
        success: true,
        session_id: 'session_123',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.saveTabState('book123', tabState);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/tab-state',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: expect.stringContaining('"active_chapter_id":"ch1"'),
        }
      );

      // Verify the session_id was generated and included
      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const requestBody = JSON.parse(callArgs[1].body);
      expect(requestBody.session_id).toMatch(/^session_\d+_[a-z0-9]+$/);
      expect(requestBody.active_chapter_id).toBe('ch1');
      expect(requestBody.open_tab_ids).toEqual(['ch1', 'ch2']);
      expect(requestBody.tab_order).toEqual(['ch1', 'ch2']);

      expect(result).toEqual(mockResponse);
    });

    it('should get tab state', async () => {
      const mockResponse = {
        active_chapter_id: 'ch1',
        open_tab_ids: ['ch1', 'ch2'],
        tab_order: ['ch1', 'ch2'],
        session_id: 'session_123',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.getTabState('book123', 'session_123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/tab-state?session_id=session_123',
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

    it('should get tab state without session id', async () => {
      const mockResponse = {
        active_chapter_id: null,
        open_tab_ids: [],
        tab_order: [],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.getTabState('book123');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/tab-state',
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

    it('should handle error when saving tab state', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 400,
        text: async () => 'Invalid tab state',
      });

      const tabState = {
        active_chapter_id: 'ch1',
        open_tab_ids: ['ch1'],
        tab_order: ['ch1'],
      };

      await expect(bookClient.saveTabState('book123', tabState)).rejects.toThrow(
        'Failed to save tab state: 400 Invalid tab state'
      );
    });
  });

  describe('Draft Generation Methods', () => {
    it('should generate chapter draft', async () => {
      const draftData = {
        question_responses: [
          { question: 'What is the main topic?', answer: 'AI development' },
        ],
        writing_style: 'professional',
        target_length: 1000,
      };

      const mockResponse = {
        success: true,
        book_id: 'book123',
        chapter_id: 'ch1',
        draft: 'Generated draft content here...',
        metadata: {
          word_count: 950,
          estimated_reading_time: 4,
          generated_at: '2025-01-01T00:00:00Z',
          model_used: 'gpt-4',
          writing_style: 'professional',
          target_length: 1000,
          actual_length: 950,
        },
        suggestions: ['Consider adding more examples'],
        message: 'Draft generated successfully',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.generateChapterDraft('book123', 'ch1', draftData);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/ch1/generate-draft',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: JSON.stringify(draftData),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle error when generating draft', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Generation failed',
      });

      const draftData = {
        question_responses: [{ question: 'Test?', answer: 'Test answer' }],
      };

      await expect(
        bookClient.generateChapterDraft('book123', 'ch1', draftData)
      ).rejects.toThrow('Failed to generate draft: 500 Generation failed');
    });
  });

  describe('Chapter Questions Methods', () => {
    it('should generate chapter questions', async () => {
      const options = {
        question_count: 5,
        difficulty_level: 'intermediate',
        question_types: ['multiple_choice', 'open_ended'],
      };

      const mockResponse = {
        questions: [
          {
            id: 'q1',
            question_text: 'What is the main concept?',
            question_type: 'open_ended',
            category: 'conceptual',
            difficulty_level: 'intermediate',
            metadata: {
              estimated_response_time: 5,
              word_count_target: 100,
            },
          },
        ],
        total_generated: 1,
        generated_at: '2025-01-01T00:00:00Z',
        metadata: {
          model_used: 'gpt-4',
          generation_time: 2.5,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.generateChapterQuestions('book123', 'ch1', options);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/ch1/generate-questions',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: JSON.stringify(options),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should get chapter questions with filters', async () => {
      const options = {
        status: 'pending',
        category: 'conceptual',
        questionType: 'open_ended' as any,
        page: 1,
        limit: 10,
      };

      const mockResponse = {
        questions: [
          {
            id: 'q1',
            question_text: 'Test question',
            status: 'pending',
            category: 'conceptual',
          },
        ],
        pagination: {
          total: 1,
          page: 1,
          per_page: 10,
          has_next: false,
          has_prev: false,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.getChapterQuestions('book123', 'ch1', options);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/ch1/questions?status=pending&category=conceptual&question_type=open_ended&page=1&limit=10',
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

    it('should save question response', async () => {
      const responseData = {
        response_text: 'This is my detailed answer',
        word_count: 6,
        quality_score: 0.8,
        response_status: 'completed',
        metadata: {
          edit_history: [],
        },
      };

      const mockResponse = {
        response: {
          id: 'resp1',
          question_id: 'q1',
          ...responseData,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
        },
        success: true,
        message: 'Response saved successfully',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await bookClient.saveQuestionResponse(
        'book123',
        'ch1',
        'q1',
        responseData as any
      );

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/books/book123/chapters/ch1/questions/q1/response',
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          credentials: 'include',
          body: JSON.stringify(responseData),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle error when generating chapter questions', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 400,
        text: async () => 'Invalid question options',
      });

      await expect(
        bookClient.generateChapterQuestions('book123', 'ch1', { question_count: -1 })
      ).rejects.toThrow('Failed to generate questions: 400 Invalid question options');
    });

    it('should handle error when getting chapter questions', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => 'Chapter not found',
      });

      await expect(
        bookClient.getChapterQuestions('book123', 'nonexistent')
      ).rejects.toThrow('Failed to get questions: 404 Chapter not found');
    });

    it('should handle error when saving question response', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 422,
        text: async () => 'Validation error',
      });

      const responseData = {
        response_text: '',
        word_count: 0,
        quality_score: 0,
        response_status: 'pending',
      };

      await expect(
        bookClient.saveQuestionResponse('book123', 'ch1', 'q1', responseData as any)
      ).rejects.toThrow('Failed to save question response: 422 Validation error');
    });
  });
});
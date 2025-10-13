/**
 * Comprehensive test suite for Book type definitions
 * Tests type guards, helper functions, and enum validation
 *
 * Coverage target: >85%
 * Pass rate target: 100%
 */

import {
  // Enums
  ChapterStatus,
  QuestionType,
  QuestionDifficulty,
  ResponseStatus,
  CollaboratorRole,
  // Type Guards
  isChapterStatus,
  isQuestionType,
  isQuestionDifficulty,
  isTocItem,
  isBookResponse,
  isQuestion,
  isQuestionResponse,
  // Helper Functions
  calculateBookWordCount,
  calculateBookProgress,
  toBookProject,
  getChapterById,
  getChaptersByLevel,
  getChildChapters,
  sortChaptersByOrder,
  // Types
  TocItem,
  BookResponse,
  Question,
  QuestionResponse,
  BookProject,
} from '../book';

// ============================================================================
// Type Guard Tests
// ============================================================================

describe('Type Guards', () => {
  describe('isChapterStatus', () => {
    it('should validate valid ChapterStatus values', () => {
      expect(isChapterStatus('draft')).toBe(true);
      expect(isChapterStatus('in-progress')).toBe(true);
      expect(isChapterStatus('completed')).toBe(true);
      expect(isChapterStatus('published')).toBe(true);
    });

    it('should validate ChapterStatus enum values', () => {
      expect(isChapterStatus(ChapterStatus.DRAFT)).toBe(true);
      expect(isChapterStatus(ChapterStatus.IN_PROGRESS)).toBe(true);
      expect(isChapterStatus(ChapterStatus.COMPLETED)).toBe(true);
      expect(isChapterStatus(ChapterStatus.PUBLISHED)).toBe(true);
    });

    it('should reject invalid string values', () => {
      expect(isChapterStatus('invalid')).toBe(false);
      expect(isChapterStatus('Draft')).toBe(false); // Case sensitive
      expect(isChapterStatus('DRAFT')).toBe(false);
      expect(isChapterStatus('')).toBe(false);
    });

    it('should reject non-string values', () => {
      expect(isChapterStatus(null)).toBe(false);
      expect(isChapterStatus(undefined)).toBe(false);
      expect(isChapterStatus(123)).toBe(false);
      expect(isChapterStatus({})).toBe(false);
      expect(isChapterStatus([])).toBe(false);
    });
  });

  describe('isQuestionType', () => {
    it('should validate valid QuestionType values', () => {
      expect(isQuestionType('character')).toBe(true);
      expect(isQuestionType('plot')).toBe(true);
      expect(isQuestionType('setting')).toBe(true);
      expect(isQuestionType('theme')).toBe(true);
      expect(isQuestionType('research')).toBe(true);
    });

    it('should validate QuestionType enum values', () => {
      expect(isQuestionType(QuestionType.CHARACTER)).toBe(true);
      expect(isQuestionType(QuestionType.PLOT)).toBe(true);
      expect(isQuestionType(QuestionType.SETTING)).toBe(true);
      expect(isQuestionType(QuestionType.THEME)).toBe(true);
      expect(isQuestionType(QuestionType.RESEARCH)).toBe(true);
    });

    it('should reject invalid values', () => {
      expect(isQuestionType('invalid')).toBe(false);
      expect(isQuestionType('CHARACTER')).toBe(false); // Case sensitive
      expect(isQuestionType(null)).toBe(false);
      expect(isQuestionType(123)).toBe(false);
    });
  });

  describe('isQuestionDifficulty', () => {
    it('should validate valid QuestionDifficulty values', () => {
      expect(isQuestionDifficulty('easy')).toBe(true);
      expect(isQuestionDifficulty('medium')).toBe(true);
      expect(isQuestionDifficulty('hard')).toBe(true);
    });

    it('should validate QuestionDifficulty enum values', () => {
      expect(isQuestionDifficulty(QuestionDifficulty.EASY)).toBe(true);
      expect(isQuestionDifficulty(QuestionDifficulty.MEDIUM)).toBe(true);
      expect(isQuestionDifficulty(QuestionDifficulty.HARD)).toBe(true);
    });

    it('should reject invalid values', () => {
      expect(isQuestionDifficulty('normal')).toBe(false);
      expect(isQuestionDifficulty('EASY')).toBe(false);
      expect(isQuestionDifficulty(null)).toBe(false);
      expect(isQuestionDifficulty(undefined)).toBe(false);
    });
  });

  describe('isTocItem', () => {
    const validTocItem: TocItem = {
      id: 'chapter-1',
      title: 'Chapter 1',
      level: 1,
      order: 1,
      status: ChapterStatus.DRAFT,
      word_count: 1000,
      estimated_reading_time: 5,
      is_active_tab: false,
      metadata: {},
    };

    it('should validate a complete valid TocItem', () => {
      expect(isTocItem(validTocItem)).toBe(true);
    });

    it('should validate TocItem with optional fields', () => {
      const tocWithOptionals: TocItem = {
        ...validTocItem,
        description: 'Chapter description',
        parent_id: 'parent-1',
        content_id: 'content-1',
        last_modified: '2024-01-01T00:00:00Z',
      };
      expect(isTocItem(tocWithOptionals)).toBe(true);
    });

    it('should reject objects missing required fields', () => {
      const missingId = { ...validTocItem };
      delete (missingId as any).id;
      expect(isTocItem(missingId)).toBe(false);

      const missingTitle = { ...validTocItem };
      delete (missingTitle as any).title;
      expect(isTocItem(missingTitle)).toBe(false);

      const missingStatus = { ...validTocItem };
      delete (missingStatus as any).status;
      expect(isTocItem(missingStatus)).toBe(false);
    });

    it('should reject objects with invalid field types', () => {
      expect(isTocItem({ ...validTocItem, id: 123 })).toBe(false);
      expect(isTocItem({ ...validTocItem, title: null })).toBe(false);
      expect(isTocItem({ ...validTocItem, level: '1' })).toBe(false);
      expect(isTocItem({ ...validTocItem, order: '1' })).toBe(false);
      expect(isTocItem({ ...validTocItem, status: 'invalid' })).toBe(false);
      expect(isTocItem({ ...validTocItem, word_count: '1000' })).toBe(false);
      expect(isTocItem({ ...validTocItem, estimated_reading_time: '5' })).toBe(false);
      expect(isTocItem({ ...validTocItem, is_active_tab: 'true' })).toBe(false);
      expect(isTocItem({ ...validTocItem, metadata: null })).toBe(false);
    });

    it('should reject non-object values', () => {
      expect(isTocItem(null)).toBe(false);
      expect(isTocItem(undefined)).toBe(false);
      expect(isTocItem('string')).toBe(false);
      expect(isTocItem(123)).toBe(false);
      expect(isTocItem([])).toBe(false);
    });
  });

  describe('isBookResponse', () => {
    const validBook: BookResponse = {
      id: 'book-1',
      title: 'Test Book',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      owner_id: 'user-1',
      toc_items: [],
      published: false,
      metadata: {},
      collaborators: [],
    };

    it('should validate a complete valid BookResponse', () => {
      expect(isBookResponse(validBook)).toBe(true);
    });

    it('should validate BookResponse with optional fields', () => {
      const bookWithOptionals: BookResponse = {
        ...validBook,
        subtitle: 'A great book',
        description: 'This is a test book',
        genre: 'Fiction',
        target_audience: 'Adults',
        cover_image_url: 'https://example.com/cover.jpg',
      };
      expect(isBookResponse(bookWithOptionals)).toBe(true);
    });

    it('should validate BookResponse with toc_items', () => {
      const tocItem: TocItem = {
        id: 'chapter-1',
        title: 'Chapter 1',
        level: 1,
        order: 1,
        status: ChapterStatus.DRAFT,
        word_count: 1000,
        estimated_reading_time: 5,
        is_active_tab: false,
        metadata: {},
      };
      const bookWithChapters = { ...validBook, toc_items: [tocItem] };
      expect(isBookResponse(bookWithChapters)).toBe(true);
    });

    it('should reject objects missing required fields', () => {
      const missingId = { ...validBook };
      delete (missingId as any).id;
      expect(isBookResponse(missingId)).toBe(false);

      const missingTitle = { ...validBook };
      delete (missingTitle as any).title;
      expect(isBookResponse(missingTitle)).toBe(false);

      const missingOwnerId = { ...validBook };
      delete (missingOwnerId as any).owner_id;
      expect(isBookResponse(missingOwnerId)).toBe(false);
    });

    it('should reject objects with invalid field types', () => {
      expect(isBookResponse({ ...validBook, id: 123 })).toBe(false);
      expect(isBookResponse({ ...validBook, title: null })).toBe(false);
      expect(isBookResponse({ ...validBook, toc_items: 'not-array' })).toBe(false);
      expect(isBookResponse({ ...validBook, published: 'true' })).toBe(false);
      expect(isBookResponse({ ...validBook, metadata: null })).toBe(false);
    });

    it('should reject non-object values', () => {
      expect(isBookResponse(null)).toBe(false);
      expect(isBookResponse(undefined)).toBe(false);
      expect(isBookResponse('book')).toBe(false);
      expect(isBookResponse([])).toBe(false);
    });
  });

  describe('isQuestion', () => {
    const validQuestion: Question = {
      id: 'q-1',
      book_id: 'book-1',
      chapter_id: 'chapter-1',
      question_text: 'What is the main character\'s motivation?',
      question_type: QuestionType.CHARACTER,
      difficulty: QuestionDifficulty.MEDIUM,
      category: 'Character Development',
      order: 1,
      generated_at: '2024-01-01T00:00:00Z',
      metadata: {
        suggested_response_length: '200-300 words',
      },
    };

    it('should validate a complete valid Question', () => {
      expect(isQuestion(validQuestion)).toBe(true);
    });

    it('should reject objects missing required fields', () => {
      const missingId = { ...validQuestion };
      delete (missingId as any).id;
      expect(isQuestion(missingId)).toBe(false);

      const missingQuestionText = { ...validQuestion };
      delete (missingQuestionText as any).question_text;
      expect(isQuestion(missingQuestionText)).toBe(false);
    });

    it('should reject objects with invalid field types', () => {
      expect(isQuestion({ ...validQuestion, id: 123 })).toBe(false);
      expect(isQuestion({ ...validQuestion, question_type: 'invalid' })).toBe(false);
      expect(isQuestion({ ...validQuestion, difficulty: 'normal' })).toBe(false);
      expect(isQuestion({ ...validQuestion, order: '1' })).toBe(false);
    });

    it('should reject non-object values', () => {
      expect(isQuestion(null)).toBe(false);
      expect(isQuestion(undefined)).toBe(false);
      expect(isQuestion('question')).toBe(false);
    });
  });

  describe('isQuestionResponse', () => {
    const validResponse: QuestionResponse = {
      id: 'qr-1',
      question_id: 'q-1',
      user_id: 'user-1',
      response_text: 'The main character is motivated by...',
      word_count: 150,
      status: ResponseStatus.DRAFT,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      last_edited_at: '2024-01-01T00:00:00Z',
      metadata: {
        edit_history: [],
      },
    };

    it('should validate a complete valid QuestionResponse', () => {
      expect(isQuestionResponse(validResponse)).toBe(true);
    });

    it('should reject objects missing required fields', () => {
      const missingId = { ...validResponse };
      delete (missingId as any).id;
      expect(isQuestionResponse(missingId)).toBe(false);

      const missingResponseText = { ...validResponse };
      delete (missingResponseText as any).response_text;
      expect(isQuestionResponse(missingResponseText)).toBe(false);
    });

    it('should reject objects with invalid field types', () => {
      expect(isQuestionResponse({ ...validResponse, id: 123 })).toBe(false);
      expect(isQuestionResponse({ ...validResponse, word_count: '150' })).toBe(false);
      expect(isQuestionResponse({ ...validResponse, user_id: null })).toBe(false);
    });

    it('should reject non-object values', () => {
      expect(isQuestionResponse(null)).toBe(false);
      expect(isQuestionResponse(undefined)).toBe(false);
    });
  });
});

// ============================================================================
// Helper Function Tests
// ============================================================================

describe('Helper Functions', () => {
  describe('calculateBookWordCount', () => {
    it('should calculate total word count from chapters', () => {
      const book: BookResponse = {
        id: 'book-1',
        title: 'Test Book',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        owner_id: 'user-1',
        published: false,
        metadata: {},
        collaborators: [],
        toc_items: [
          {
            id: 'ch-1',
            title: 'Chapter 1',
            level: 1,
            order: 1,
            status: ChapterStatus.DRAFT,
            word_count: 1000,
            estimated_reading_time: 5,
            is_active_tab: false,
            metadata: {},
          },
          {
            id: 'ch-2',
            title: 'Chapter 2',
            level: 1,
            order: 2,
            status: ChapterStatus.COMPLETED,
            word_count: 1500,
            estimated_reading_time: 8,
            is_active_tab: false,
            metadata: {},
          },
          {
            id: 'ch-3',
            title: 'Chapter 3',
            level: 1,
            order: 3,
            status: ChapterStatus.IN_PROGRESS,
            word_count: 750,
            estimated_reading_time: 4,
            is_active_tab: false,
            metadata: {},
          },
        ],
      };

      expect(calculateBookWordCount(book)).toBe(3250);
    });

    it('should return 0 for book with no chapters', () => {
      const emptyBook: BookResponse = {
        id: 'book-1',
        title: 'Empty Book',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        owner_id: 'user-1',
        published: false,
        metadata: {},
        collaborators: [],
        toc_items: [],
      };

      expect(calculateBookWordCount(emptyBook)).toBe(0);
    });

    it('should handle chapters with zero word count', () => {
      const book: BookResponse = {
        id: 'book-1',
        title: 'Test Book',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        owner_id: 'user-1',
        published: false,
        metadata: {},
        collaborators: [],
        toc_items: [
          {
            id: 'ch-1',
            title: 'Empty Chapter',
            level: 1,
            order: 1,
            status: ChapterStatus.DRAFT,
            word_count: 0,
            estimated_reading_time: 0,
            is_active_tab: false,
            metadata: {},
          },
        ],
      };

      expect(calculateBookWordCount(book)).toBe(0);
    });
  });

  describe('calculateBookProgress', () => {
    it('should calculate completion percentage correctly', () => {
      const book: BookResponse = {
        id: 'book-1',
        title: 'Test Book',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        owner_id: 'user-1',
        published: false,
        metadata: {},
        collaborators: [],
        toc_items: [
          {
            id: 'ch-1',
            title: 'Chapter 1',
            level: 1,
            order: 1,
            status: ChapterStatus.COMPLETED,
            word_count: 1000,
            estimated_reading_time: 5,
            is_active_tab: false,
            metadata: {},
          },
          {
            id: 'ch-2',
            title: 'Chapter 2',
            level: 1,
            order: 2,
            status: ChapterStatus.PUBLISHED,
            word_count: 1500,
            estimated_reading_time: 8,
            is_active_tab: false,
            metadata: {},
          },
          {
            id: 'ch-3',
            title: 'Chapter 3',
            level: 1,
            order: 3,
            status: ChapterStatus.IN_PROGRESS,
            word_count: 750,
            estimated_reading_time: 4,
            is_active_tab: false,
            metadata: {},
          },
          {
            id: 'ch-4',
            title: 'Chapter 4',
            level: 1,
            order: 4,
            status: ChapterStatus.DRAFT,
            word_count: 0,
            estimated_reading_time: 0,
            is_active_tab: false,
            metadata: {},
          },
        ],
      };

      // 2 completed/published out of 4 chapters = 50%
      expect(calculateBookProgress(book)).toBe(50);
    });

    it('should return 0 for book with no chapters', () => {
      const emptyBook: BookResponse = {
        id: 'book-1',
        title: 'Empty Book',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        owner_id: 'user-1',
        published: false,
        metadata: {},
        collaborators: [],
        toc_items: [],
      };

      expect(calculateBookProgress(emptyBook)).toBe(0);
    });

    it('should return 100 for fully completed book', () => {
      const completeBook: BookResponse = {
        id: 'book-1',
        title: 'Complete Book',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        owner_id: 'user-1',
        published: false,
        metadata: {},
        collaborators: [],
        toc_items: [
          {
            id: 'ch-1',
            title: 'Chapter 1',
            level: 1,
            order: 1,
            status: ChapterStatus.COMPLETED,
            word_count: 1000,
            estimated_reading_time: 5,
            is_active_tab: false,
            metadata: {},
          },
          {
            id: 'ch-2',
            title: 'Chapter 2',
            level: 1,
            order: 2,
            status: ChapterStatus.PUBLISHED,
            word_count: 1500,
            estimated_reading_time: 8,
            is_active_tab: false,
            metadata: {},
          },
        ],
      };

      expect(calculateBookProgress(completeBook)).toBe(100);
    });

    it('should return 0 for book with no completed chapters', () => {
      const draftBook: BookResponse = {
        id: 'book-1',
        title: 'Draft Book',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        owner_id: 'user-1',
        published: false,
        metadata: {},
        collaborators: [],
        toc_items: [
          {
            id: 'ch-1',
            title: 'Chapter 1',
            level: 1,
            order: 1,
            status: ChapterStatus.DRAFT,
            word_count: 0,
            estimated_reading_time: 0,
            is_active_tab: false,
            metadata: {},
          },
          {
            id: 'ch-2',
            title: 'Chapter 2',
            level: 1,
            order: 2,
            status: ChapterStatus.IN_PROGRESS,
            word_count: 500,
            estimated_reading_time: 3,
            is_active_tab: false,
            metadata: {},
          },
        ],
      };

      expect(calculateBookProgress(draftBook)).toBe(0);
    });

    it('should round percentages correctly', () => {
      const book: BookResponse = {
        id: 'book-1',
        title: 'Test Book',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        owner_id: 'user-1',
        published: false,
        metadata: {},
        collaborators: [],
        toc_items: [
          { id: '1', title: 'Ch 1', level: 1, order: 1, status: ChapterStatus.COMPLETED, word_count: 100, estimated_reading_time: 1, is_active_tab: false, metadata: {} },
          { id: '2', title: 'Ch 2', level: 1, order: 2, status: ChapterStatus.DRAFT, word_count: 0, estimated_reading_time: 0, is_active_tab: false, metadata: {} },
          { id: '3', title: 'Ch 3', level: 1, order: 3, status: ChapterStatus.DRAFT, word_count: 0, estimated_reading_time: 0, is_active_tab: false, metadata: {} },
        ],
      };

      // 1 out of 3 = 33.33%, should round to 33
      expect(calculateBookProgress(book)).toBe(33);
    });
  });

  describe('toBookProject', () => {
    it('should convert BookResponse to BookProject format', () => {
      const book: BookResponse = {
        id: 'book-1',
        title: 'Test Book',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        owner_id: 'user-1',
        published: false,
        metadata: {},
        collaborators: [],
        toc_items: [
          {
            id: 'ch-1',
            title: 'Chapter 1',
            level: 1,
            order: 1,
            status: ChapterStatus.COMPLETED,
            word_count: 1000,
            estimated_reading_time: 5,
            is_active_tab: false,
            metadata: {},
          },
          {
            id: 'ch-2',
            title: 'Chapter 2',
            level: 1,
            order: 2,
            status: ChapterStatus.DRAFT,
            word_count: 500,
            estimated_reading_time: 3,
            is_active_tab: false,
            metadata: {},
          },
        ],
      };

      const project = toBookProject(book);

      expect(project).toMatchObject({
        ...book,
        chapters: 2,
        progress: 50, // 1 out of 2 completed
        word_count: 1500,
      });
    });

    it('should handle empty book correctly', () => {
      const emptyBook: BookResponse = {
        id: 'book-1',
        title: 'Empty Book',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        owner_id: 'user-1',
        published: false,
        metadata: {},
        collaborators: [],
        toc_items: [],
      };

      const project = toBookProject(emptyBook);

      expect(project.chapters).toBe(0);
      expect(project.progress).toBe(0);
      expect(project.word_count).toBe(0);
    });
  });

  describe('getChapterById', () => {
    const book: BookResponse = {
      id: 'book-1',
      title: 'Test Book',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      owner_id: 'user-1',
      published: false,
      metadata: {},
      collaborators: [],
      toc_items: [
        {
          id: 'ch-1',
          title: 'Chapter 1',
          level: 1,
          order: 1,
          status: ChapterStatus.DRAFT,
          word_count: 1000,
          estimated_reading_time: 5,
          is_active_tab: false,
          metadata: {},
        },
        {
          id: 'ch-2',
          title: 'Chapter 2',
          level: 1,
          order: 2,
          status: ChapterStatus.COMPLETED,
          word_count: 1500,
          estimated_reading_time: 8,
          is_active_tab: false,
          metadata: {},
        },
      ],
    };

    it('should find chapter by ID', () => {
      const chapter = getChapterById(book, 'ch-1');
      expect(chapter).toBeDefined();
      expect(chapter?.id).toBe('ch-1');
      expect(chapter?.title).toBe('Chapter 1');
    });

    it('should return undefined for non-existent ID', () => {
      const chapter = getChapterById(book, 'non-existent');
      expect(chapter).toBeUndefined();
    });

    it('should return undefined for empty book', () => {
      const emptyBook: BookResponse = {
        ...book,
        toc_items: [],
      };
      const chapter = getChapterById(emptyBook, 'ch-1');
      expect(chapter).toBeUndefined();
    });
  });

  describe('getChaptersByLevel', () => {
    const book: BookResponse = {
      id: 'book-1',
      title: 'Test Book',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      owner_id: 'user-1',
      published: false,
      metadata: {},
      collaborators: [],
      toc_items: [
        { id: 'ch-1', title: 'Chapter 1', level: 1, order: 1, status: ChapterStatus.DRAFT, word_count: 1000, estimated_reading_time: 5, is_active_tab: false, metadata: {} },
        { id: 'sec-1-1', title: 'Section 1.1', level: 2, order: 2, status: ChapterStatus.DRAFT, word_count: 500, estimated_reading_time: 3, is_active_tab: false, metadata: {} },
        { id: 'sec-1-2', title: 'Section 1.2', level: 2, order: 3, status: ChapterStatus.DRAFT, word_count: 500, estimated_reading_time: 3, is_active_tab: false, metadata: {} },
        { id: 'ch-2', title: 'Chapter 2', level: 1, order: 4, status: ChapterStatus.COMPLETED, word_count: 1500, estimated_reading_time: 8, is_active_tab: false, metadata: {} },
        { id: 'subsec-1-1-1', title: 'Subsection 1.1.1', level: 3, order: 5, status: ChapterStatus.DRAFT, word_count: 250, estimated_reading_time: 2, is_active_tab: false, metadata: {} },
      ],
    };

    it('should get all chapters at level 1', () => {
      const chapters = getChaptersByLevel(book, 1);
      expect(chapters).toHaveLength(2);
      expect(chapters[0].id).toBe('ch-1');
      expect(chapters[1].id).toBe('ch-2');
    });

    it('should get all sections at level 2', () => {
      const sections = getChaptersByLevel(book, 2);
      expect(sections).toHaveLength(2);
      expect(sections.every(s => s.level === 2)).toBe(true);
    });

    it('should get subsections at level 3', () => {
      const subsections = getChaptersByLevel(book, 3);
      expect(subsections).toHaveLength(1);
      expect(subsections[0].id).toBe('subsec-1-1-1');
    });

    it('should return empty array for non-existent level', () => {
      const chapters = getChaptersByLevel(book, 5);
      expect(chapters).toEqual([]);
    });

    it('should return empty array for empty book', () => {
      const emptyBook: BookResponse = { ...book, toc_items: [] };
      const chapters = getChaptersByLevel(emptyBook, 1);
      expect(chapters).toEqual([]);
    });
  });

  describe('getChildChapters', () => {
    const book: BookResponse = {
      id: 'book-1',
      title: 'Test Book',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      owner_id: 'user-1',
      published: false,
      metadata: {},
      collaborators: [],
      toc_items: [
        { id: 'ch-1', title: 'Chapter 1', level: 1, order: 1, parent_id: undefined, status: ChapterStatus.DRAFT, word_count: 1000, estimated_reading_time: 5, is_active_tab: false, metadata: {} },
        { id: 'sec-1-1', title: 'Section 1.1', level: 2, order: 2, parent_id: 'ch-1', status: ChapterStatus.DRAFT, word_count: 500, estimated_reading_time: 3, is_active_tab: false, metadata: {} },
        { id: 'sec-1-2', title: 'Section 1.2', level: 2, order: 3, parent_id: 'ch-1', status: ChapterStatus.DRAFT, word_count: 500, estimated_reading_time: 3, is_active_tab: false, metadata: {} },
        { id: 'ch-2', title: 'Chapter 2', level: 1, order: 4, parent_id: undefined, status: ChapterStatus.COMPLETED, word_count: 1500, estimated_reading_time: 8, is_active_tab: false, metadata: {} },
        { id: 'subsec-1-1-1', title: 'Subsection 1.1.1', level: 3, order: 5, parent_id: 'sec-1-1', status: ChapterStatus.DRAFT, word_count: 250, estimated_reading_time: 2, is_active_tab: false, metadata: {} },
      ],
    };

    it('should get all child chapters of a parent', () => {
      const children = getChildChapters(book, 'ch-1');
      expect(children).toHaveLength(2);
      expect(children[0].id).toBe('sec-1-1');
      expect(children[1].id).toBe('sec-1-2');
    });

    it('should get nested children', () => {
      const children = getChildChapters(book, 'sec-1-1');
      expect(children).toHaveLength(1);
      expect(children[0].id).toBe('subsec-1-1-1');
    });

    it('should return empty array for chapter with no children', () => {
      const children = getChildChapters(book, 'ch-2');
      expect(children).toEqual([]);
    });

    it('should return empty array for non-existent parent', () => {
      const children = getChildChapters(book, 'non-existent');
      expect(children).toEqual([]);
    });
  });

  describe('sortChaptersByOrder', () => {
    it('should sort chapters by order property', () => {
      const chapters: TocItem[] = [
        { id: 'ch-3', title: 'Chapter 3', level: 1, order: 3, status: ChapterStatus.DRAFT, word_count: 1000, estimated_reading_time: 5, is_active_tab: false, metadata: {} },
        { id: 'ch-1', title: 'Chapter 1', level: 1, order: 1, status: ChapterStatus.DRAFT, word_count: 1000, estimated_reading_time: 5, is_active_tab: false, metadata: {} },
        { id: 'ch-2', title: 'Chapter 2', level: 1, order: 2, status: ChapterStatus.DRAFT, word_count: 1000, estimated_reading_time: 5, is_active_tab: false, metadata: {} },
      ];

      const sorted = sortChaptersByOrder(chapters);

      expect(sorted[0].id).toBe('ch-1');
      expect(sorted[1].id).toBe('ch-2');
      expect(sorted[2].id).toBe('ch-3');
    });

    it('should not mutate the original array', () => {
      const chapters: TocItem[] = [
        { id: 'ch-3', title: 'Chapter 3', level: 1, order: 3, status: ChapterStatus.DRAFT, word_count: 1000, estimated_reading_time: 5, is_active_tab: false, metadata: {} },
        { id: 'ch-1', title: 'Chapter 1', level: 1, order: 1, status: ChapterStatus.DRAFT, word_count: 1000, estimated_reading_time: 5, is_active_tab: false, metadata: {} },
      ];

      const sorted = sortChaptersByOrder(chapters);

      // Original should still be in original order
      expect(chapters[0].id).toBe('ch-3');
      expect(chapters[1].id).toBe('ch-1');

      // Sorted should be in correct order
      expect(sorted[0].id).toBe('ch-1');
      expect(sorted[1].id).toBe('ch-3');
    });

    it('should handle empty array', () => {
      const sorted = sortChaptersByOrder([]);
      expect(sorted).toEqual([]);
    });

    it('should handle single chapter', () => {
      const chapters: TocItem[] = [
        { id: 'ch-1', title: 'Chapter 1', level: 1, order: 1, status: ChapterStatus.DRAFT, word_count: 1000, estimated_reading_time: 5, is_active_tab: false, metadata: {} },
      ];

      const sorted = sortChaptersByOrder(chapters);
      expect(sorted).toHaveLength(1);
      expect(sorted[0].id).toBe('ch-1');
    });

    it('should handle chapters with same order', () => {
      const chapters: TocItem[] = [
        { id: 'ch-2', title: 'Chapter 2', level: 1, order: 1, status: ChapterStatus.DRAFT, word_count: 1000, estimated_reading_time: 5, is_active_tab: false, metadata: {} },
        { id: 'ch-1', title: 'Chapter 1', level: 1, order: 1, status: ChapterStatus.DRAFT, word_count: 1000, estimated_reading_time: 5, is_active_tab: false, metadata: {} },
      ];

      const sorted = sortChaptersByOrder(chapters);
      expect(sorted).toHaveLength(2);
      // Should maintain relative order for same order values
    });
  });
});

// ============================================================================
// Edge Cases and Integration Tests
// ============================================================================

describe('Edge Cases and Integration', () => {
  describe('Enum value consistency', () => {
    it('should have consistent ChapterStatus enum values', () => {
      expect(ChapterStatus.DRAFT).toBe('draft');
      expect(ChapterStatus.IN_PROGRESS).toBe('in-progress');
      expect(ChapterStatus.COMPLETED).toBe('completed');
      expect(ChapterStatus.PUBLISHED).toBe('published');
    });

    it('should have consistent QuestionType enum values', () => {
      expect(QuestionType.CHARACTER).toBe('character');
      expect(QuestionType.PLOT).toBe('plot');
      expect(QuestionType.SETTING).toBe('setting');
      expect(QuestionType.THEME).toBe('theme');
      expect(QuestionType.RESEARCH).toBe('research');
    });

    it('should have consistent QuestionDifficulty enum values', () => {
      expect(QuestionDifficulty.EASY).toBe('easy');
      expect(QuestionDifficulty.MEDIUM).toBe('medium');
      expect(QuestionDifficulty.HARD).toBe('hard');
    });

    it('should have consistent ResponseStatus enum values', () => {
      expect(ResponseStatus.DRAFT).toBe('draft');
      expect(ResponseStatus.COMPLETED).toBe('completed');
    });

    it('should have consistent CollaboratorRole enum values', () => {
      expect(CollaboratorRole.VIEWER).toBe('viewer');
      expect(CollaboratorRole.EDITOR).toBe('editor');
      expect(CollaboratorRole.CO_AUTHOR).toBe('co-author');
    });
  });

  describe('Type guard boundary conditions', () => {
    it('should handle empty strings correctly', () => {
      expect(isChapterStatus('')).toBe(false);
      expect(isQuestionType('')).toBe(false);
      expect(isQuestionDifficulty('')).toBe(false);
    });

    it('should handle null and undefined consistently', () => {
      expect(isChapterStatus(null)).toBe(false);
      expect(isChapterStatus(undefined)).toBe(false);
      expect(isQuestionType(null)).toBe(false);
      expect(isQuestionType(undefined)).toBe(false);
    });

    it('should handle objects with partial fields', () => {
      const partialTocItem = {
        id: 'ch-1',
        title: 'Chapter 1',
        // Missing other required fields
      };
      expect(isTocItem(partialTocItem)).toBe(false);
    });
  });

  describe('Helper function composition', () => {
    it('should work correctly when chaining helper functions', () => {
      const book: BookResponse = {
        id: 'book-1',
        title: 'Test Book',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        owner_id: 'user-1',
        published: false,
        metadata: {},
        collaborators: [],
        toc_items: [
          { id: 'ch-1', title: 'Chapter 1', level: 1, order: 1, status: ChapterStatus.COMPLETED, word_count: 1000, estimated_reading_time: 5, is_active_tab: false, metadata: {} },
          { id: 'ch-2', title: 'Chapter 2', level: 1, order: 2, status: ChapterStatus.DRAFT, word_count: 500, estimated_reading_time: 3, is_active_tab: false, metadata: {} },
        ],
      };

      // Chain: get chapters -> sort -> calculate stats
      const level1Chapters = getChaptersByLevel(book, 1);
      const sortedChapters = sortChaptersByOrder(level1Chapters);
      const totalWords = sortedChapters.reduce((sum, ch) => sum + ch.word_count, 0);

      expect(sortedChapters[0].id).toBe('ch-1');
      expect(totalWords).toBe(1500);
    });
  });
});

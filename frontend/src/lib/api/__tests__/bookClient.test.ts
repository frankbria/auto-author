/**
 * Supplementary unit tests for BookClient covering methods and branches
 * not exercised by src/__tests__/bookClient.test.tsx.
 *
 * Coverage targets:
 *  - Custom baseUrl constructor
 *  - setTokenProvider / getAuthToken (tokenProvider branch)
 *  - getBook 401/403 specific error
 *  - createBook / updateBook / updateToc error paths
 *  - saveQuestionResponses / getQuestionResponses (404 + error)
 *  - updateBulkChapterStatus / getTabState error paths
 *  - transformChapterStyle (success + error)
 *  - getQuestionResponse (success + error)
 *  - saveQuestionResponsesBatch (success + error)
 *  - rateQuestion (success + error)
 *  - getChapterQuestionProgress (success + error)
 *  - regenerateChapterQuestions (success + error)
 *  - exportPDF / exportDOCX (success with options)
 *  - exportError structured-message branch (detail.message object)
 *  - getExportFormats (success + error)
 *  - analyzeSummaryWithErrorHandling (success + error)
 *  - generateQuestionsWithErrorHandling (success + error)
 *  - generateTocWithErrorHandling (success + error)
 *  - generateChapterQuestionsWithErrorHandling (success + error)
 *  - generateChapterDraftWithErrorHandling (success + error)
 *  - getChapterQAResponses (multiple scenarios)
 */

import { BookClient, bookClient } from '@/lib/api/bookClient';

// Mock aiErrorHandler to avoid showErrorNotification side-effects in jsdom
jest.mock('@/lib/api/aiErrorHandler', () => ({
  handleAIServiceError: jest.fn().mockResolvedValue({
    error: 'AI service error',
    canRetry: false,
  }),
}));

// Pull the mock reference after jest.mock hoisting
import { handleAIServiceError } from '@/lib/api/aiErrorHandler';
const mockHandleAIServiceError = handleAIServiceError as jest.Mock;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Creates a minimal successful fetch response with a JSON body. */
function okJson(body: unknown) {
  return {
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
    blob: async () => new Blob([JSON.stringify(body)]),
  };
}

/** Creates a failed fetch response. */
function errorResponse(status: number, bodyText = 'Error', jsonBody?: unknown) {
  return {
    ok: false,
    status,
    text: async () => bodyText,
    json: async () => jsonBody ?? { detail: bodyText },
    blob: async () => new Blob([bodyText]),
  };
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  // clearAllMocks clears call counts but does NOT reset mockResolvedValueOnce queues.
  // mockReset clears both call records AND queued return values, preventing test
  // pollution when a test fails before consuming all its mocked fetch responses.
  (global.fetch as jest.Mock).mockReset();
  mockHandleAIServiceError.mockReset();
  mockHandleAIServiceError.mockResolvedValue({
    error: 'AI service error',
    canRetry: false,
  });
  // Restore a sensible default so tests that don't set up explicit mocks don't fail
  (global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({}),
    text: async () => '',
    blob: async () => new Blob(),
  });
});

// ---------------------------------------------------------------------------
// Constructor – custom baseUrl
// ---------------------------------------------------------------------------

describe('BookClient – constructor', () => {
  it('uses the provided custom baseUrl for all requests', async () => {
    const customUrl = 'https://custom.api.example.com/v2';
    const client = new BookClient(customUrl);

    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson([]));

    await client.getUserBooks();

    expect(global.fetch).toHaveBeenCalledWith(
      `${customUrl}/books/`,
      expect.any(Object)
    );
  });

  it('falls back to the default baseUrl when none is supplied', async () => {
    const client = new BookClient();

    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson([]));

    await client.getUserBooks();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/books/'),
      expect.any(Object)
    );
  });
});

// ---------------------------------------------------------------------------
// setTokenProvider / getAuthToken (tokenProvider branch)
// ---------------------------------------------------------------------------

describe('BookClient – token provider', () => {
  it('uses a token returned by the provider in the Authorization header', async () => {
    const client = new BookClient();
    const provider = jest.fn().mockResolvedValue('provider-token-xyz');
    client.setTokenProvider(provider);

    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson([]));

    await client.getUserBooks();

    expect(provider).toHaveBeenCalledTimes(1);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer provider-token-xyz',
        }),
      })
    );
  });

  it('omits the Authorization header when the provider returns null', async () => {
    const client = new BookClient();
    const provider = jest.fn().mockResolvedValue(null);
    client.setTokenProvider(provider);

    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson([]));

    await client.getUserBooks();

    expect(provider).toHaveBeenCalledTimes(1);
    const callHeaders = (global.fetch as jest.Mock).mock.calls[0][1].headers as Record<string, string>;
    expect(callHeaders['Authorization']).toBeUndefined();
  });

  it('setAuthToken takes precedence over no-provider state', async () => {
    const client = new BookClient();
    client.setAuthToken('static-token');

    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson([]));

    await client.getUserBooks();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer static-token',
        }),
      })
    );
  });
});

// ---------------------------------------------------------------------------
// getBook – 401/403 specific error path
// ---------------------------------------------------------------------------

describe('BookClient.getBook – auth errors', () => {
  it('throws an authorization-specific message on 401', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(401, 'Unauthorized'));

    await expect(bookClient.getBook('book-xyz')).rejects.toThrow(
      'You are not authorized to view this book. Please check your login or permissions.'
    );
  });

  it('throws an authorization-specific message on 403', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(403, 'Forbidden'));

    await expect(bookClient.getBook('book-xyz')).rejects.toThrow(
      'You are not authorized to view this book. Please check your login or permissions.'
    );
  });
});

// ---------------------------------------------------------------------------
// createBook – error path
// ---------------------------------------------------------------------------

describe('BookClient.createBook – errors', () => {
  it('throws with status and body text on failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(422, 'Title is required'));

    await expect(
      bookClient.createBook({ title: '' })
    ).rejects.toThrow('Failed to create book: 422 Title is required');
  });
});

// ---------------------------------------------------------------------------
// updateBook – error path
// ---------------------------------------------------------------------------

describe('BookClient.updateBook – errors', () => {
  it('throws with status and body text on failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(403, 'Forbidden'));

    await expect(
      bookClient.updateBook('book123', { title: 'New Title' })
    ).rejects.toThrow('Failed to update book: 403 Forbidden');
  });
});

// ---------------------------------------------------------------------------
// updateToc – error path
// ---------------------------------------------------------------------------

describe('BookClient.updateToc – errors', () => {
  it('surfaces backend detail.message from a structured error', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ detail: { message: 'TOC save service unavailable' } }),
    });

    await expect(
      bookClient.updateToc('book123', {
        chapters: [],
        total_chapters: 0,
        estimated_pages: 0,
        structure_notes: '',
      })
    ).rejects.toThrow('TOC save service unavailable');
  });

  it('falls back to generic message when body is not parseable', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => { throw new Error('bad json'); },
    });

    await expect(
      bookClient.updateToc('book123', {
        chapters: [],
        total_chapters: 0,
        estimated_pages: 0,
        structure_notes: '',
      })
    ).rejects.toThrow('Failed to save table of contents. Please try again.');
  });
});

// ---------------------------------------------------------------------------
// saveQuestionResponses – error path
// ---------------------------------------------------------------------------

describe('BookClient.saveQuestionResponses – errors', () => {
  it('throws with status and body text on failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(400, 'Invalid responses'));

    await expect(
      bookClient.saveQuestionResponses('book123', [])
    ).rejects.toThrow('Failed to save question responses: 400 Invalid responses');
  });
});

// ---------------------------------------------------------------------------
// getQuestionResponses – 404 returns empty, other errors throw
// ---------------------------------------------------------------------------

describe('BookClient.getQuestionResponses', () => {
  it('returns empty responses object on 404 instead of throwing', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(404, 'Not found'));

    const result = await bookClient.getQuestionResponses('book123');

    expect(result).toEqual({ responses: [], status: 'not_provided' });
  });

  it('throws on non-404 errors', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(500, 'Server error'));

    await expect(bookClient.getQuestionResponses('book123')).rejects.toThrow(
      'Failed to get question responses: 500 Server error'
    );
  });
});

// ---------------------------------------------------------------------------
// updateBulkChapterStatus – error path
// ---------------------------------------------------------------------------

describe('BookClient.updateBulkChapterStatus – errors', () => {
  it('throws with status and body text on failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(400, 'Invalid status value'));

    await expect(
      bookClient.updateBulkChapterStatus('book123', ['ch1', 'ch2'], 'invalid' as any)
    ).rejects.toThrow('Failed to update bulk chapter status: 400 Invalid status value');
  });
});

// ---------------------------------------------------------------------------
// getTabState – error path
// ---------------------------------------------------------------------------

describe('BookClient.getTabState – errors', () => {
  it('throws with status and body text on failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(401, 'Unauthorized'));

    await expect(bookClient.getTabState('book123')).rejects.toThrow(
      'Failed to get tab state: 401 Unauthorized'
    );
  });
});

// ---------------------------------------------------------------------------
// transformChapterStyle
// ---------------------------------------------------------------------------

describe('BookClient.transformChapterStyle', () => {
  const bookId = 'book123';
  const chapterId = 'ch456';
  const requestData = {
    content: 'Original chapter content here.',
    target_style: 'academic',
  };

  const mockSuccess = {
    success: true,
    book_id: bookId,
    chapter_id: chapterId,
    transformed: 'Rewritten in academic style.',
    metadata: {
      target_style: 'academic',
      style_label: 'Academic',
      original_word_count: 4,
      transformed_word_count: 4,
      model_used: 'claude-3',
      generated_at: '2025-01-01T00:00:00Z',
    },
    message: 'Style transformation complete.',
  };

  it('calls the correct endpoint with POST and returns the transformed result', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(mockSuccess));

    const result = await bookClient.transformChapterStyle(bookId, chapterId, requestData);

    expect(global.fetch).toHaveBeenCalledWith(
      `http://localhost:8000/api/v1/books/${bookId}/chapters/${chapterId}/transform-style`,
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify(requestData),
      })
    );
    expect(result).toEqual(mockSuccess);
  });

  it('throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(503, 'Service unavailable'));

    await expect(
      bookClient.transformChapterStyle(bookId, chapterId, requestData)
    ).rejects.toThrow('Failed to transform style: 503 Service unavailable');
  });
});

// ---------------------------------------------------------------------------
// getQuestionResponse
// ---------------------------------------------------------------------------

describe('BookClient.getQuestionResponse', () => {
  it('returns the response data on success', async () => {
    const mockResponse = {
      response: {
        id: 'resp1',
        question_id: 'q1',
        response_text: 'My detailed answer',
        status: 'completed',
      },
      has_response: true,
      success: true,
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(mockResponse));

    const result = await bookClient.getQuestionResponse('book123', 'ch1', 'q1');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/books/book123/chapters/ch1/questions/q1/response',
      expect.objectContaining({ credentials: 'include' })
    );
    expect(result).toEqual(mockResponse);
  });

  it('throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(404, 'Question not found'));

    await expect(
      bookClient.getQuestionResponse('book123', 'ch1', 'q-none')
    ).rejects.toThrow('Failed to get question response: 404 Question not found');
  });
});

// ---------------------------------------------------------------------------
// saveQuestionResponsesBatch
// ---------------------------------------------------------------------------

describe('BookClient.saveQuestionResponsesBatch', () => {
  const bookId = 'book123';
  const chapterId = 'ch1';
  const responses = [
    { question_id: 'q1', response_text: 'Answer one', status: 'completed' as const },
    { question_id: 'q2', response_text: 'Draft answer', status: 'draft' as const },
  ];

  it('POSTs the batch and returns success result', async () => {
    const mockResult = {
      success: true,
      total: 2,
      saved: 2,
      failed: 0,
      results: [
        { index: 0, question_id: 'q1', response_id: 'r1', success: true },
        { index: 1, question_id: 'q2', response_id: 'r2', success: true },
      ],
      message: 'All responses saved.',
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(mockResult));

    const result = await bookClient.saveQuestionResponsesBatch(bookId, chapterId, responses);

    expect(global.fetch).toHaveBeenCalledWith(
      `http://localhost:8000/api/v1/books/${bookId}/chapters/${chapterId}/questions/responses/batch`,
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify(responses),
      })
    );
    expect(result).toEqual(mockResult);
  });

  it('throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(400, 'Batch too large'));

    await expect(
      bookClient.saveQuestionResponsesBatch(bookId, chapterId, responses)
    ).rejects.toThrow('Failed to save question responses batch: 400 Batch too large');
  });
});

// ---------------------------------------------------------------------------
// rateQuestion
// ---------------------------------------------------------------------------

describe('BookClient.rateQuestion', () => {
  const bookId = 'book123';
  const chapterId = 'ch1';
  const questionId = 'q1';
  const ratingData = { rating: 4, feedback: 'Great question' } as any;

  it('POSTs the rating and returns the saved rating', async () => {
    const mockResult = {
      rating: {
        id: 'rat1',
        question_id: questionId,
        rating: 4,
        feedback: 'Great question',
        created_at: '2025-01-01T00:00:00Z',
      },
      success: true,
      message: 'Rating saved.',
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(mockResult));

    const result = await bookClient.rateQuestion(bookId, chapterId, questionId, ratingData);

    expect(global.fetch).toHaveBeenCalledWith(
      `http://localhost:8000/api/v1/books/${bookId}/chapters/${chapterId}/questions/${questionId}/rating`,
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify(ratingData),
      })
    );
    expect(result).toEqual(mockResult);
  });

  it('throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(422, 'Rating out of range'));

    await expect(
      bookClient.rateQuestion(bookId, chapterId, questionId, ratingData)
    ).rejects.toThrow('Failed to rate question: 422 Rating out of range');
  });
});

// ---------------------------------------------------------------------------
// getChapterQuestionProgress
// ---------------------------------------------------------------------------

describe('BookClient.getChapterQuestionProgress', () => {
  const bookId = 'book123';
  const chapterId = 'ch1';

  it('GETs the progress data and returns it', async () => {
    const mockProgress = {
      total: 10,
      completed: 7,
      in_progress: 2,
      not_started: 1,
      completion_percentage: 70,
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(mockProgress));

    const result = await bookClient.getChapterQuestionProgress(bookId, chapterId);

    expect(global.fetch).toHaveBeenCalledWith(
      `http://localhost:8000/api/v1/books/${bookId}/chapters/${chapterId}/question-progress`,
      expect.objectContaining({ credentials: 'include' })
    );
    expect(result).toEqual(mockProgress);
  });

  it('throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(404, 'Chapter not found'));

    await expect(
      bookClient.getChapterQuestionProgress(bookId, chapterId)
    ).rejects.toThrow('Failed to get question progress: 404 Chapter not found');
  });
});

// ---------------------------------------------------------------------------
// regenerateChapterQuestions
// ---------------------------------------------------------------------------

describe('BookClient.regenerateChapterQuestions', () => {
  const bookId = 'book123';
  const chapterId = 'ch1';

  const mockGenerateResponse = {
    questions: [{ id: 'q1', question_text: 'What is...?', status: 'pending' }],
    total_generated: 1,
    generated_at: '2025-01-01T00:00:00Z',
  } as any;

  it('posts to regenerate-questions with preserve_responses=true by default', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(mockGenerateResponse));

    const result = await bookClient.regenerateChapterQuestions(bookId, chapterId, {});

    expect(global.fetch).toHaveBeenCalledWith(
      `http://localhost:8000/api/v1/books/${bookId}/chapters/${chapterId}/regenerate-questions?preserve_responses=true`,
      expect.objectContaining({ method: 'POST', credentials: 'include' })
    );
    expect(result).toEqual(mockGenerateResponse);
  });

  it('passes preserve_responses=false when specified', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(mockGenerateResponse));

    await bookClient.regenerateChapterQuestions(bookId, chapterId, {}, false);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('preserve_responses=false'),
      expect.any(Object)
    );
  });

  it('throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(500, 'Generation failed'));

    await expect(
      bookClient.regenerateChapterQuestions(bookId, chapterId, {})
    ).rejects.toThrow('Failed to regenerate questions: 500 Generation failed');
  });
});

// ---------------------------------------------------------------------------
// exportPDF – success with and without options
// ---------------------------------------------------------------------------

describe('BookClient.exportPDF', () => {
  it('GETs the PDF blob without options (no query params)', async () => {
    const blob = new Blob(['%PDF-1.4'], { type: 'application/pdf' });
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      blob: async () => blob,
    });

    const result = await bookClient.exportPDF('book123');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/books/book123/export/pdf?',
      expect.objectContaining({ credentials: 'include' })
    );
    expect(result).toBeInstanceOf(Blob);
  });

  it('appends includeEmptyChapters and pageSize as query params', async () => {
    const blob = new Blob(['%PDF-1.4'], { type: 'application/pdf' });
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      blob: async () => blob,
    });

    await bookClient.exportPDF('book123', { includeEmptyChapters: true, pageSize: 'A4' });

    const calledUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(calledUrl).toContain('include_empty_chapters=true');
    expect(calledUrl).toContain('page_size=A4');
  });

  it('appends includeEmptyChapters=false when specified', async () => {
    const blob = new Blob(['%PDF-1.4']);
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      blob: async () => blob,
    });

    await bookClient.exportPDF('book123', { includeEmptyChapters: false });

    const calledUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(calledUrl).toContain('include_empty_chapters=false');
  });
});

// ---------------------------------------------------------------------------
// exportDOCX – success with and without options
// ---------------------------------------------------------------------------

describe('BookClient.exportDOCX', () => {
  it('GETs the DOCX blob without options', async () => {
    const blob = new Blob(['PK...'], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      blob: async () => blob,
    });

    const result = await bookClient.exportDOCX('book123');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/books/book123/export/docx?',
      expect.objectContaining({ credentials: 'include' })
    );
    expect(result).toBeInstanceOf(Blob);
  });

  it('appends includeEmptyChapters when specified', async () => {
    const blob = new Blob(['PK...']);
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      blob: async () => blob,
    });

    await bookClient.exportDOCX('book123', { includeEmptyChapters: true });

    const calledUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(calledUrl).toContain('include_empty_chapters=true');
  });
});

// ---------------------------------------------------------------------------
// exportEPUB – success with and without options
// ---------------------------------------------------------------------------

describe('BookClient.exportEPUB', () => {
  it('GETs the EPUB blob without options', async () => {
    const blob = new Blob(['PK...'], { type: 'application/epub+zip' });
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      blob: async () => blob,
    });

    const result = await bookClient.exportEPUB('book123');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/books/book123/export/epub?',
      expect.objectContaining({ credentials: 'include' })
    );
    expect(result).toBeInstanceOf(Blob);
  });

  it('appends includeEmptyChapters when specified', async () => {
    const blob = new Blob(['PK...']);
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      blob: async () => blob,
    });

    await bookClient.exportEPUB('book123', { includeEmptyChapters: true });

    const calledUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(calledUrl).toContain('include_empty_chapters=true');
  });
});

// ---------------------------------------------------------------------------
// exportError – structured detail.message branch
// ---------------------------------------------------------------------------

describe('BookClient exportError – detail.message object branch', () => {
  it('surfaces detail.message from an object-shaped detail on PDF export failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ detail: { message: 'PDF generator offline' } }),
    });

    await expect(bookClient.exportPDF('book123')).rejects.toMatchObject({
      statusCode: 503,
      message: 'PDF generator offline',
      userMessage: 'PDF generator offline',
    });
  });

  it('surfaces detail.message from an object-shaped detail on DOCX export failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ detail: { message: 'DOCX generator offline' } }),
    });

    await expect(bookClient.exportDOCX('book123')).rejects.toMatchObject({
      statusCode: 503,
      message: 'DOCX generator offline',
      userMessage: 'DOCX generator offline',
    });
  });

  it('surfaces a plain-string detail on PDF export failure (string detail branch)', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'This book has no chapter content yet.' }),
    });

    await expect(bookClient.exportPDF('book123')).rejects.toMatchObject({
      statusCode: 400,
      message: 'This book has no chapter content yet.',
      userMessage: 'This book has no chapter content yet.',
    });
  });

  it('falls back to status-based message when detail is absent', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({}),
    });

    await expect(bookClient.exportPDF('book123')).rejects.toMatchObject({
      statusCode: 500,
      message: 'Export failed: 500',
    });
  });
});

// ---------------------------------------------------------------------------
// getExportFormats
// ---------------------------------------------------------------------------

describe('BookClient.getExportFormats', () => {
  it('returns available export formats and book stats', async () => {
    const mockResponse = {
      formats: [
        {
          format: 'pdf',
          name: 'PDF',
          description: 'Portable Document Format',
          mime_type: 'application/pdf',
          extension: 'pdf',
          available: true,
        },
        {
          format: 'docx',
          name: 'Word Document',
          description: 'Microsoft Word',
          mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          extension: 'docx',
          available: true,
        },
      ],
      book_stats: {
        total_chapters: 5,
        chapters_with_content: 3,
        total_word_count: 10000,
        estimated_pages: 40,
      },
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(mockResponse));

    const result = await bookClient.getExportFormats('book123');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/books/book123/export/formats',
      expect.objectContaining({ credentials: 'include' })
    );
    expect(result).toEqual(mockResponse);
  });

  it('throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(404, 'Book not found'));

    await expect(bookClient.getExportFormats('book123')).rejects.toThrow(
      'Failed to get export formats: 404 Book not found'
    );
  });
});

// ---------------------------------------------------------------------------
// analyzeSummaryWithErrorHandling
// ---------------------------------------------------------------------------

describe('BookClient.analyzeSummaryWithErrorHandling', () => {
  const analysisResult = {
    book_id: 'book123',
    analysis: {
      is_ready_for_toc: true,
      confidence_score: 0.9,
      analysis: 'Great summary',
      suggestions: [],
      word_count: 200,
      character_count: 1000,
      meets_minimum_requirements: true,
    },
    analyzed_at: '2025-01-01T00:00:00Z',
  };

  it('returns { data: result } on success', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(analysisResult));

    const result = await bookClient.analyzeSummaryWithErrorHandling('book123');

    expect(result).toEqual({ data: analysisResult });
    expect(mockHandleAIServiceError).not.toHaveBeenCalled();
  });

  it('delegates to handleAIServiceError on failure and returns its result', async () => {
    const aiError = { error: 'AI failed', canRetry: true };
    mockHandleAIServiceError.mockResolvedValueOnce(aiError);

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ detail: { message: 'Service down' } }),
    });

    const onRetry = jest.fn();
    const result = await bookClient.analyzeSummaryWithErrorHandling('book123', onRetry);

    expect(mockHandleAIServiceError).toHaveBeenCalledTimes(1);
    expect(mockHandleAIServiceError).toHaveBeenCalledWith(
      expect.any(Error),
      onRetry
    );
    expect(result).toEqual(aiError);
  });
});

// ---------------------------------------------------------------------------
// generateQuestionsWithErrorHandling
// ---------------------------------------------------------------------------

describe('BookClient.generateQuestionsWithErrorHandling', () => {
  it('returns { data: result } on success', async () => {
    const questionsResult = { questions: ['Q1?', 'Q2?'] };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(questionsResult));

    const result = await bookClient.generateQuestionsWithErrorHandling('book123');

    expect(result).toEqual({ data: questionsResult });
    expect(mockHandleAIServiceError).not.toHaveBeenCalled();
  });

  it('delegates to handleAIServiceError on failure', async () => {
    const aiError = { error: 'Rate limited', canRetry: true, retryAfter: 60 };
    mockHandleAIServiceError.mockResolvedValueOnce(aiError);

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 429,
      json: async () => ({ detail: { message: 'Rate limit exceeded' } }),
    });

    const result = await bookClient.generateQuestionsWithErrorHandling('book123');

    expect(mockHandleAIServiceError).toHaveBeenCalledTimes(1);
    expect(result).toEqual(aiError);
  });
});

// ---------------------------------------------------------------------------
// generateTocWithErrorHandling
// ---------------------------------------------------------------------------

describe('BookClient.generateTocWithErrorHandling', () => {
  const tocResult = {
    toc: {
      chapters: [
        {
          id: 'ch1',
          title: 'Intro',
          description: 'Introduction',
          level: 1,
          order: 1,
          subchapters: [],
        },
      ],
      total_chapters: 1,
      estimated_pages: 10,
      structure_notes: '',
    },
    success: true,
    chapters_count: 1,
    has_subchapters: false,
  };

  it('returns { data: result } on success', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(tocResult));

    const result = await bookClient.generateTocWithErrorHandling('book123', [
      { question: 'Topic?', answer: 'AI' },
    ]);

    expect(result).toEqual({ data: tocResult });
    expect(mockHandleAIServiceError).not.toHaveBeenCalled();
  });

  it('delegates to handleAIServiceError on failure', async () => {
    const aiError = { error: 'TOC generation failed', canRetry: false };
    mockHandleAIServiceError.mockResolvedValueOnce(aiError);

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => { throw new Error('not json'); },
    });

    const onRetry = jest.fn();
    const result = await bookClient.generateTocWithErrorHandling(
      'book123',
      [{ question: 'Q?', answer: 'A' }],
      onRetry
    );

    expect(mockHandleAIServiceError).toHaveBeenCalledTimes(1);
    expect(result).toEqual(aiError);
  });
});

// ---------------------------------------------------------------------------
// generateChapterQuestionsWithErrorHandling
// ---------------------------------------------------------------------------

describe('BookClient.generateChapterQuestionsWithErrorHandling', () => {
  const generatedQuestions = {
    questions: [{ id: 'q1', question_text: 'What is?', status: 'pending' }],
    total_generated: 1,
    generated_at: '2025-01-01T00:00:00Z',
  } as any;

  it('returns { data: result } on success', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(generatedQuestions));

    const result = await bookClient.generateChapterQuestionsWithErrorHandling(
      'book123',
      'ch1',
      {}
    );

    expect(result).toEqual({ data: generatedQuestions });
    expect(mockHandleAIServiceError).not.toHaveBeenCalled();
  });

  it('delegates to handleAIServiceError on failure', async () => {
    const aiError = { error: 'Chapter questions failed', canRetry: false };
    mockHandleAIServiceError.mockResolvedValueOnce(aiError);

    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(500, 'Server error'));

    const onRetry = jest.fn();
    const result = await bookClient.generateChapterQuestionsWithErrorHandling(
      'book123',
      'ch1',
      {},
      onRetry
    );

    expect(mockHandleAIServiceError).toHaveBeenCalledTimes(1);
    expect(result).toEqual(aiError);
  });
});

// ---------------------------------------------------------------------------
// generateChapterDraftWithErrorHandling
// ---------------------------------------------------------------------------

describe('BookClient.generateChapterDraftWithErrorHandling', () => {
  const draftData = {
    question_responses: [{ question: 'Q?', answer: 'A' }],
    writing_style: 'professional',
    target_length: 500,
  };

  const draftResult = {
    success: true,
    book_id: 'book123',
    chapter_id: 'ch1',
    draft: 'Generated draft...',
    metadata: {
      word_count: 480,
      estimated_reading_time: 2,
      generated_at: '2025-01-01T00:00:00Z',
      model_used: 'claude-3',
      writing_style: 'professional',
      target_length: 500,
      actual_length: 480,
    },
    suggestions: [],
    message: 'Draft generated.',
  };

  it('returns { data: result } on success', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(draftResult));

    const result = await bookClient.generateChapterDraftWithErrorHandling(
      'book123',
      'ch1',
      draftData
    );

    expect(result).toEqual({ data: draftResult });
    expect(mockHandleAIServiceError).not.toHaveBeenCalled();
  });

  it('delegates to handleAIServiceError on failure', async () => {
    const aiError = { error: 'Draft generation failed', canRetry: true };
    mockHandleAIServiceError.mockResolvedValueOnce(aiError);

    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(503, 'AI unavailable'));

    const onRetry = jest.fn();
    const result = await bookClient.generateChapterDraftWithErrorHandling(
      'book123',
      'ch1',
      draftData,
      onRetry
    );

    expect(mockHandleAIServiceError).toHaveBeenCalledWith(expect.any(Error), onRetry);
    expect(result).toEqual(aiError);
  });
});

// ---------------------------------------------------------------------------
// getChapterQAResponses – comprehensive scenarios
// ---------------------------------------------------------------------------

describe('BookClient.getChapterQAResponses', () => {
  const bookId = 'book123';
  const chapterId = 'ch1';

  /** Helper: mock a getChapterQuestions response */
  function mockQuestionsPage(questions: unknown[], pages: number) {
    (global.fetch as jest.Mock).mockResolvedValueOnce(
      okJson({ questions, pages, total: questions.length * pages })
    );
  }

  /** Helper: mock a getQuestionResponse response */
  function mockQResponse(hasResponse: boolean, status?: string, responseText?: string) {
    const body = hasResponse
      ? {
          has_response: true,
          response: {
            id: 'r1',
            question_id: 'q1',
            response_text: responseText ?? 'Some answer',
            status: status ?? 'completed',
          },
          success: true,
        }
      : { has_response: false, response: null, success: true };

    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(body));
  }

  it('returns aggregated responses for a single-page result with completed responses', async () => {
    const questions = [
      { id: 'q1', question_text: 'What is your goal?' },
      { id: 'q2', question_text: 'Who is your audience?' },
    ];

    mockQuestionsPage(questions, 1);
    mockQResponse(true, 'completed', 'My goal is X');
    mockQResponse(true, 'completed', 'Developers');

    const result = await bookClient.getChapterQAResponses(bookId, chapterId);

    expect(result.totalQuestions).toBe(2);
    expect(result.completedCount).toBe(2);
    expect(result.inProgressCount).toBe(0);
    expect(result.responses).toHaveLength(2);
    expect(result.responses[0]).toMatchObject({
      question: 'What is your goal?',
      answer: 'My goal is X',
      status: 'completed',
    });
  });

  it('includes draft responses in inProgressCount', async () => {
    const questions = [
      { id: 'q1', question_text: 'Q completed' },
      { id: 'q2', question_text: 'Q in progress' },
    ];

    mockQuestionsPage(questions, 1);
    mockQResponse(true, 'completed', 'Done answer');
    mockQResponse(true, 'draft', 'Work in progress');

    const result = await bookClient.getChapterQAResponses(bookId, chapterId);

    expect(result.completedCount).toBe(1);
    expect(result.inProgressCount).toBe(1);
    expect(result.responses).toHaveLength(2);
    expect(result.responses[1]).toMatchObject({ status: 'draft', answer: 'Work in progress' });
  });

  it('skips questions with no response (has_response = false)', async () => {
    const questions = [{ id: 'q1', question_text: 'Unanswered Q' }];

    mockQuestionsPage(questions, 1);
    mockQResponse(false);

    const result = await bookClient.getChapterQAResponses(bookId, chapterId);

    expect(result.totalQuestions).toBe(1);
    expect(result.responses).toHaveLength(0);
    expect(result.completedCount).toBe(0);
    expect(result.inProgressCount).toBe(0);
  });

  it('handles pagination across multiple pages', async () => {
    // getChapterQAResponses fetches ALL pages first, THEN fetches individual responses.
    // Mock order must match: page-1-questions, page-2-questions, q1-response, q2-response.

    // Page 1 questions (pages=2 signals there is a second page)
    (global.fetch as jest.Mock).mockResolvedValueOnce(
      okJson({ questions: [{ id: 'q1', question_text: 'Page 1 Q' }], pages: 2, total: 2 })
    );
    // Page 2 questions
    (global.fetch as jest.Mock).mockResolvedValueOnce(
      okJson({ questions: [{ id: 'q2', question_text: 'Page 2 Q' }], pages: 2, total: 2 })
    );
    // Response for q1 (fetched after all pages are loaded)
    mockQResponse(true, 'completed', 'Page 1 answer');
    // Response for q2
    mockQResponse(true, 'completed', 'Page 2 answer');

    const result = await bookClient.getChapterQAResponses(bookId, chapterId);

    expect(result.totalQuestions).toBe(2);
    expect(result.completedCount).toBe(2);
    expect(result.responses).toHaveLength(2);
  });

  it('continues gracefully when getQuestionResponse throws for one question', async () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    const questions = [
      { id: 'q1', question_text: 'Q that errors' },
      { id: 'q2', question_text: 'Q that succeeds' },
    ];

    mockQuestionsPage(questions, 1);

    // q1 fetch throws a network error
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));
    // q2 fetch succeeds
    mockQResponse(true, 'completed', 'Good answer');

    const result = await bookClient.getChapterQAResponses(bookId, chapterId);

    // Should only have q2's response
    expect(result.totalQuestions).toBe(2);
    expect(result.responses).toHaveLength(1);
    expect(result.responses[0].questionId).toBe('q2');
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      expect.stringContaining('Error fetching response for question q1'),
      expect.any(Error)
    );

    consoleErrorSpy.mockRestore();
  });

  it('returns empty when there are no questions', async () => {
    mockQuestionsPage([], 1);

    const result = await bookClient.getChapterQAResponses(bookId, chapterId);

    expect(result.totalQuestions).toBe(0);
    expect(result.responses).toHaveLength(0);
    expect(result.completedCount).toBe(0);
    expect(result.inProgressCount).toBe(0);
  });

  it('passes correct pagination params to getChapterQuestions', async () => {
    mockQuestionsPage([], 1);

    await bookClient.getChapterQAResponses(bookId, chapterId);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('page=1&limit=50'),
      expect.any(Object)
    );
  });
});

// ---------------------------------------------------------------------------
// aiError helper – detail as plain string vs object.message
// This exercises the branch in aiError() itself via checkTocReadiness
// ---------------------------------------------------------------------------

describe('BookClient aiError helper – detail string branch', () => {
  it('surfaces a plain-string detail from checkTocReadiness failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Summary too short' }),
    });

    await expect(bookClient.checkTocReadiness('book123')).rejects.toThrow(
      'Summary too short'
    );
  });
});

// ---------------------------------------------------------------------------
// Core CRUD – happy paths (standalone coverage for src/lib/api/ command)
// The original test file at src/__tests__/bookClient.test.tsx covers these too;
// these tests exist so `npx jest src/lib/api/` alone reaches ≥85%.
// ---------------------------------------------------------------------------

describe('BookClient core CRUD – success paths', () => {
  const BOOK_ID = 'book-abc';
  const CHAPTER_ID = 'ch-xyz';

  // getUserBooks
  it('getUserBooks returns an array of books', async () => {
    const books = [{ id: BOOK_ID, title: 'Book A' }];
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(books));

    const result = await bookClient.getUserBooks();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/books/'),
      expect.objectContaining({ credentials: 'include' })
    );
    expect(result).toEqual(books);
  });

  it('getUserBooks throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(401, 'Unauthorized'));
    await expect(bookClient.getUserBooks()).rejects.toThrow('Failed to fetch books: 401');
  });

  // getBook
  it('getBook returns a single book', async () => {
    const book = { id: BOOK_ID, title: 'My Book' };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(book));

    const result = await bookClient.getBook(BOOK_ID);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/books/${BOOK_ID}`),
      expect.objectContaining({ credentials: 'include' })
    );
    expect(result).toEqual(book);
  });

  it('getBook throws a generic message on non-auth errors', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(404, 'Not Found'));
    await expect(bookClient.getBook(BOOK_ID)).rejects.toThrow('Failed to fetch book: 404');
  });

  // createBook
  it('createBook POSTs and returns the new book', async () => {
    const payload = { title: 'New Book', genre: 'Fiction' };
    const created = { id: 'new-id', ...payload };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(created));

    const result = await bookClient.createBook(payload);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/books/'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(payload),
        credentials: 'include',
      })
    );
    expect(result).toEqual(created);
  });

  // updateBook
  it('updateBook PATCHes and returns the updated book', async () => {
    const updates = { title: 'Renamed' };
    const updated = { id: BOOK_ID, ...updates };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(updated));

    const result = await bookClient.updateBook(BOOK_ID, updates);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/books/${BOOK_ID}`),
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify(updates),
        credentials: 'include',
      })
    );
    expect(result).toEqual(updated);
  });

  // deleteBook
  it('deleteBook sends DELETE and resolves when ok', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true, status: 204 });

    await expect(bookClient.deleteBook(BOOK_ID)).resolves.toBeUndefined();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/books/${BOOK_ID}`),
      expect.objectContaining({ method: 'DELETE', credentials: 'include' })
    );
  });

  it('deleteBook throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(403, 'Forbidden'));
    await expect(bookClient.deleteBook(BOOK_ID)).rejects.toThrow(
      'Failed to delete book: 403 Forbidden'
    );
  });

  // getBookSummary
  it('getBookSummary returns the summary', async () => {
    const data = { summary: 'A great book.', summary_history: [] };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.getBookSummary(BOOK_ID);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/books/${BOOK_ID}/summary`),
      expect.objectContaining({ credentials: 'include' })
    );
    expect(result).toEqual(data);
  });

  it('getBookSummary throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(404, 'Not found'));
    await expect(bookClient.getBookSummary(BOOK_ID)).rejects.toThrow(
      'Failed to fetch book summary: 404 Not found'
    );
  });

  // saveBookSummary
  it('saveBookSummary PUTs the summary and returns saved data', async () => {
    const saved = { summary: 'Updated summary', success: true };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(saved));

    const result = await bookClient.saveBookSummary(BOOK_ID, 'Updated summary');

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/books/${BOOK_ID}/summary`),
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ summary: 'Updated summary' }),
        credentials: 'include',
      })
    );
    expect(result).toEqual(saved);
  });

  it('saveBookSummary throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(400, 'Invalid'));
    await expect(bookClient.saveBookSummary(BOOK_ID, 'x')).rejects.toThrow(
      'Failed to save book summary: 400 Invalid'
    );
  });

  // checkTocReadiness – success (error already covered above)
  it('checkTocReadiness returns readiness data on success', async () => {
    const data = {
      is_ready_for_toc: true,
      confidence_score: 0.85,
      analysis: 'Good',
      suggestions: [],
      word_count: 300,
      character_count: 1500,
      meets_minimum_requirements: true,
    };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.checkTocReadiness(BOOK_ID);
    expect(result).toEqual(data);
  });

  // analyzeSummary – success and error
  it('analyzeSummary POSTs and returns analysis result', async () => {
    const data = {
      book_id: BOOK_ID,
      analysis: { is_ready_for_toc: false, confidence_score: 0.4, analysis: 'Too short', suggestions: ['Add more'], word_count: 50, character_count: 250, meets_minimum_requirements: false },
      analyzed_at: '2025-01-01T00:00:00Z',
    };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.analyzeSummary(BOOK_ID);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/books/${BOOK_ID}/analyze-summary`),
      expect.objectContaining({ method: 'POST', credentials: 'include' })
    );
    expect(result).toEqual(data);
  });

  it('analyzeSummary surfaces AI error detail on failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ detail: { message: 'Analysis service down' } }),
    });
    await expect(bookClient.analyzeSummary(BOOK_ID)).rejects.toThrow('Analysis service down');
  });

  // generateQuestions – success and error
  it('generateQuestions POSTs and returns questions', async () => {
    const data = { questions: ['What is the theme?'] };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.generateQuestions(BOOK_ID);
    expect(result).toEqual(data);
  });

  it('generateQuestions surfaces AI error on failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ detail: { message: 'Question generator offline' } }),
    });
    await expect(bookClient.generateQuestions(BOOK_ID)).rejects.toThrow(
      'Question generator offline'
    );
  });

  // generateToc – success and AI error
  it('generateToc POSTs and returns the TOC', async () => {
    const data = {
      toc: { chapters: [], total_chapters: 0, estimated_pages: 0, structure_notes: '' },
      success: true,
      chapters_count: 0,
      has_subchapters: false,
    };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.generateToc(BOOK_ID, [{ question: 'Q?', answer: 'A' }]);
    expect(result).toEqual(data);
  });

  it('generateToc surfaces plain-string detail on AI failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Not enough responses' }),
    });
    await expect(
      bookClient.generateToc(BOOK_ID, [{ question: 'Q?', answer: 'A' }])
    ).rejects.toThrow('Not enough responses');
  });

  // getToc – success and error
  it('getToc GETs and returns the TOC structure', async () => {
    const data = {
      toc: { chapters: [{ id: 'c1', title: 'Intro', description: '', level: 1, order: 1, subchapters: [] }], total_chapters: 1, estimated_pages: 10, structure_notes: '' },
    };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.getToc(BOOK_ID);
    expect(result).toEqual(data);
  });

  it('getToc throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(404, 'No TOC'));
    await expect(bookClient.getToc(BOOK_ID)).rejects.toThrow('Failed to get TOC: 404 No TOC');
  });

  // updateToc – success
  it('updateToc PUTs and returns the updated TOC', async () => {
    const tocPayload = { chapters: [], total_chapters: 0, estimated_pages: 0, structure_notes: '' };
    const saved = { toc: tocPayload, success: true };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(saved));

    const result = await bookClient.updateToc(BOOK_ID, tocPayload);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/books/${BOOK_ID}/toc`),
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ toc: tocPayload }),
        credentials: 'include',
      })
    );
    expect(result).toEqual(saved);
  });

  // saveQuestionResponses – success
  it('saveQuestionResponses PUTs responses and returns the result', async () => {
    const data = { book_id: BOOK_ID, responses_saved: 1, answered_at: '2025-01-01', ready_for_toc_generation: true };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.saveQuestionResponses(BOOK_ID, [] as any);
    expect(result).toEqual(data);
  });

  // getQuestionResponses – success
  it('getQuestionResponses returns the responses', async () => {
    const data = { responses: [], status: 'completed' };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.getQuestionResponses(BOOK_ID);
    expect(result).toEqual(data);
  });

  // saveChapterContent – success and error
  it('saveChapterContent PATCHes and returns the save result', async () => {
    const data = { book_id: BOOK_ID, chapter_id: CHAPTER_ID, success: true, message: 'Saved', metadata_updated: true };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.saveChapterContent(BOOK_ID, CHAPTER_ID, '<p>Content</p>');

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/books/${BOOK_ID}/chapters/${CHAPTER_ID}/content`),
      expect.objectContaining({ method: 'PATCH', credentials: 'include' })
    );
    expect(result).toEqual(data);
  });

  it('saveChapterContent throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(403, 'Forbidden'));
    await expect(bookClient.saveChapterContent(BOOK_ID, CHAPTER_ID, 'x')).rejects.toThrow(
      'Failed to save chapter content: 403 Forbidden'
    );
  });

  // getChapterContent – success and error
  it('getChapterContent GETs and returns the chapter content', async () => {
    const data = { content: '<p>Hello</p>', chapter_id: CHAPTER_ID, book_id: BOOK_ID };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.getChapterContent(BOOK_ID, CHAPTER_ID);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/books/${BOOK_ID}/chapters/${CHAPTER_ID}/content`),
      expect.objectContaining({ method: 'GET', credentials: 'include' })
    );
    expect(result).toEqual(data);
  });

  it('getChapterContent with custom flags appends query params', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson({ content: '', chapter_id: CHAPTER_ID, book_id: BOOK_ID }));

    await bookClient.getChapterContent(BOOK_ID, CHAPTER_ID, false, false);

    const calledUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(calledUrl).toContain('include_metadata=false');
    expect(calledUrl).toContain('track_access=false');
  });

  it('getChapterContent throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(404, 'Not found'));
    await expect(bookClient.getChapterContent(BOOK_ID, CHAPTER_ID)).rejects.toThrow(
      'Failed to get chapter content: 404 Not found'
    );
  });

  // getChaptersMetadata – success and error
  it('getChaptersMetadata GETs and returns the metadata', async () => {
    const data = { book_id: BOOK_ID, chapters: [], total_chapters: 0, completion_stats: { draft: 0, in_progress: 0, completed: 0, published: 0 } };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.getChaptersMetadata(BOOK_ID);
    expect(result).toEqual(data);
  });

  it('getChaptersMetadata throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(404, 'Book not found'));
    await expect(bookClient.getChaptersMetadata(BOOK_ID)).rejects.toThrow(
      'Failed to get chapters metadata: 404 Book not found'
    );
  });

  // updateChapterStatus – success and error
  it('updateChapterStatus PATCHes and resolves', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson({ success: true }));

    await bookClient.updateChapterStatus(BOOK_ID, CHAPTER_ID, 'completed' as any);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/books/${BOOK_ID}/chapters/bulk-status`),
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ chapter_ids: [CHAPTER_ID], status: 'completed', update_timestamp: true }),
        credentials: 'include',
      })
    );
  });

  it('updateChapterStatus throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(400, 'Bad status'));
    await expect(
      bookClient.updateChapterStatus(BOOK_ID, CHAPTER_ID, 'bad' as any)
    ).rejects.toThrow('Failed to update chapter status: 400 Bad status');
  });

  // updateBulkChapterStatus – success
  it('updateBulkChapterStatus PATCHes multiple chapters', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson({ success: true }));

    await bookClient.updateBulkChapterStatus(BOOK_ID, [CHAPTER_ID, 'ch2'], 'in-progress' as any);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/chapters/bulk-status'),
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ chapter_ids: [CHAPTER_ID, 'ch2'], status: 'in-progress', update_timestamp: true }),
      })
    );
  });

  // saveTabState – success and error
  it('saveTabState POSTs the tab state and resolves', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson({ success: true }));

    const tabState = { active_chapter_id: CHAPTER_ID, open_tab_ids: [CHAPTER_ID], tab_order: [CHAPTER_ID] };
    await bookClient.saveTabState(BOOK_ID, tabState);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/books/${BOOK_ID}/chapters/tab-state`),
      expect.objectContaining({ method: 'POST', credentials: 'include' })
    );
  });

  it('saveTabState throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(400, 'Bad state'));
    await expect(
      bookClient.saveTabState(BOOK_ID, { active_chapter_id: null, open_tab_ids: [], tab_order: [] })
    ).rejects.toThrow('Failed to save tab state: 400 Bad state');
  });

  // getTabState – success (error already covered)
  it('getTabState GETs and returns the tab state', async () => {
    const data = { active_chapter_id: CHAPTER_ID, open_tab_ids: [CHAPTER_ID], tab_order: [CHAPTER_ID] };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.getTabState(BOOK_ID);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/books/${BOOK_ID}/chapters/tab-state`),
      expect.objectContaining({ credentials: 'include' })
    );
    expect(result).toEqual(data);
  });

  // getTabState – with sessionId query param
  it('getTabState appends session_id when provided', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson({ active_chapter_id: null, open_tab_ids: [], tab_order: [] }));

    await bookClient.getTabState(BOOK_ID, 'sess-abc');

    const calledUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(calledUrl).toContain('session_id=sess-abc');
  });

  // generateChapterDraft – success and error
  it('generateChapterDraft POSTs and returns the draft', async () => {
    const data = {
      success: true, book_id: BOOK_ID, chapter_id: CHAPTER_ID, draft: 'Draft text',
      metadata: { word_count: 100, estimated_reading_time: 1, generated_at: '', model_used: '', writing_style: 'professional', target_length: 500, actual_length: 480 },
      suggestions: [], message: 'Done',
    };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.generateChapterDraft(BOOK_ID, CHAPTER_ID, { question_responses: [{ question: 'Q', answer: 'A' }] });
    expect(result).toEqual(data);
  });

  it('generateChapterDraft throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(500, 'AI down'));
    await expect(
      bookClient.generateChapterDraft(BOOK_ID, CHAPTER_ID, { question_responses: [] })
    ).rejects.toThrow('Failed to generate draft: 500 AI down');
  });

  // generateChapterQuestions – success and error
  it('generateChapterQuestions POSTs and returns questions', async () => {
    const data = { questions: [], total_generated: 0, generated_at: '' } as any;
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.generateChapterQuestions(BOOK_ID, CHAPTER_ID, {});
    expect(result).toEqual(data);
  });

  it('generateChapterQuestions throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(400, 'Bad opts'));
    await expect(bookClient.generateChapterQuestions(BOOK_ID, CHAPTER_ID, {})).rejects.toThrow(
      'Failed to generate questions: 400 Bad opts'
    );
  });

  // getChapterQuestions – success and error (no filter options)
  it('getChapterQuestions GETs questions without filters', async () => {
    const data = { questions: [], pages: 1, total: 0 } as any;
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.getChapterQuestions(BOOK_ID, CHAPTER_ID);
    expect(result).toEqual(data);
  });

  it('getChapterQuestions with all filter options builds the correct URL', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson({ questions: [], pages: 1, total: 0 }));

    await bookClient.getChapterQuestions(BOOK_ID, CHAPTER_ID, {
      status: 'pending',
      category: 'conceptual',
      questionType: 'open_ended' as any,
      page: 2,
      limit: 20,
    });

    const calledUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(calledUrl).toContain('status=pending');
    expect(calledUrl).toContain('category=conceptual');
    expect(calledUrl).toContain('question_type=open_ended');
    expect(calledUrl).toContain('page=2');
    expect(calledUrl).toContain('limit=20');
  });

  it('getChapterQuestions throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(404, 'Not found'));
    await expect(bookClient.getChapterQuestions(BOOK_ID, CHAPTER_ID)).rejects.toThrow(
      'Failed to get questions: 404 Not found'
    );
  });

  // saveQuestionResponse – success and error
  it('saveQuestionResponse PUTs and returns saved response', async () => {
    const data = { response: { id: 'r1', question_id: 'q1', response_text: 'Answer', status: 'completed' }, success: true, message: 'Saved' };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.saveQuestionResponse(BOOK_ID, CHAPTER_ID, 'q1', { response_text: 'Answer' } as any);
    expect(result).toEqual(data);
  });

  it('saveQuestionResponse throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(422, 'Validation error'));
    await expect(
      bookClient.saveQuestionResponse(BOOK_ID, CHAPTER_ID, 'q1', {} as any)
    ).rejects.toThrow('Failed to save question response: 422 Validation error');
  });

  // createChapter – success and error
  it('createChapter POSTs and returns the new chapter', async () => {
    const data = { id: CHAPTER_ID, title: 'Ch 1', content: '', order: 1, status: 'draft', created_at: '', updated_at: '' };
    (global.fetch as jest.Mock).mockResolvedValueOnce(okJson(data));

    const result = await bookClient.createChapter(BOOK_ID, { title: 'Ch 1' });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/books/${BOOK_ID}/chapters`),
      expect.objectContaining({ method: 'POST', credentials: 'include' })
    );
    expect(result).toEqual(data);
  });

  it('createChapter throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(400, 'Bad data'));
    await expect(bookClient.createChapter(BOOK_ID, { title: '' })).rejects.toThrow(
      'Failed to create chapter: 400 Bad data'
    );
  });

  // deleteChapter – success and error
  it('deleteChapter sends DELETE and resolves', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true, status: 204 });

    await expect(bookClient.deleteChapter(BOOK_ID, CHAPTER_ID)).resolves.toBeUndefined();
  });

  it('deleteChapter throws on non-ok response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse(404, 'Chapter not found'));
    await expect(bookClient.deleteChapter(BOOK_ID, CHAPTER_ID)).rejects.toThrow(
      'Failed to delete chapter: 404 Chapter not found'
    );
  });
});

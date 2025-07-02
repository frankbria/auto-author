import bookClient from './bookClient';

export interface DraftGenerationRequest {
  question_responses: Array<{
    question: string;
    answer: string;
  }>;
  writing_style: string;
  target_length: number;
}

export interface DraftGenerationResponse {
  draft: string;
  metadata: {
    word_count: number;
    estimated_reading_time: number;
    generated_at: string;
    model_used: string;
    writing_style: string;
    target_length: number;
    actual_length: number;
  };
  suggestions?: string[];
}

export interface DraftContent {
  content: string;
  metadata: {
    word_count: number;
    last_modified: string;
    auto_saved: boolean;
  };
}

/**
 * Client for managing chapter drafts and AI-generated content
 * Delegates to bookClient for actual API calls
 */
class DraftClient {
  /**
   * Generate a chapter draft from question responses
   */
  async generateChapterDraft(
    bookId: string, 
    chapterId: string, 
    request: DraftGenerationRequest
  ): Promise<DraftGenerationResponse> {
    try {
      return await bookClient.generateChapterDraft(bookId, chapterId, request);
    } catch (error) {
      console.error('Failed to generate chapter draft:', error);
      throw new Error(`Draft generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get draft content for a chapter
   */
  async getDraftContent(bookId: string, chapterId: string): Promise<DraftContent> {
    try {
      const response = await bookClient.getChapterContent(bookId, chapterId);
      return {
        content: response.content || '',
        metadata: {
          word_count: response.metadata?.word_count || 0,
          last_modified: response.metadata?.last_modified || new Date().toISOString(),
          auto_saved: false // This would need to be tracked separately
        }
      };
    } catch (error) {
      console.error('Failed to get draft content:', error);
      throw new Error(`Failed to retrieve draft: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Save draft content for a chapter
   */
  async saveDraftContent(
    bookId: string, 
    chapterId: string, 
    content: string,
    autoSave: boolean = false
  ): Promise<void> {
    try {
      await bookClient.saveChapterContent(bookId, chapterId, content);
    } catch (error) {
      console.error('Failed to save draft content:', error);
      throw new Error(`Failed to save draft: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get chapter writing progress and statistics
   */
  async getDraftStatistics(bookId: string, chapterId: string): Promise<{
    word_count: number;
    last_saved: string;
    draft_versions: number;
  }> {
    try {
      const response = await bookClient.getChapterContent(bookId, chapterId);
      return {
        word_count: response.metadata?.word_count || 0,
        last_saved: response.metadata?.last_modified || new Date().toISOString(),
        draft_versions: 1 // This would need versioning support in the backend
      };
    } catch (error) {
      console.error('Failed to get draft statistics:', error);
      throw new Error(`Failed to get statistics: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
}

// Export singleton instance
export const draftClient = new DraftClient();

export default draftClient;
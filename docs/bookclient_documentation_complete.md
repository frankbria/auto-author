# BookClient JSDoc Documentation - Complete Reference

This document contains the complete JSDoc documentation for all BookClient methods.
Use this as reference for the implementation.

## Summary & TOC Generation Methods

### generateQuestions
```typescript
/**
 * Generate clarifying questions for TOC creation
 *
 * Uses AI to generate relevant questions that help refine the book's
 * table of contents structure. Questions are based on the book summary
 * and target audience.
 *
 * @param bookId - Unique identifier for the book
 * @returns Promise resolving to generated questions array
 *
 * @throws {Error} When generation fails
 *   - 400: Book has no summary or insufficient detail
 *   - 401: User is not authenticated
 *   - 403: User does not have access to this book
 *   - 404: Book not found
 *   - 500: Server error or AI service unavailable
 *
 * @example
 * ```typescript
 * // Generate questions
 * const result = await bookClient.generateQuestions(bookId);
 * console.log(`Generated ${result.questions.length} questions`);
 *
 * result.questions.forEach((q, i) => {
 *   console.log(`${i + 1}. ${q}`);
 * });
 *
 * // With error handling
 * try {
 *   const { questions } = await bookClient.generateQuestions(bookId);
 *   // Display questions to user for answers
 * } catch (error) {
 *   if (error.message.includes('400')) {
 *     alert('Please add more detail to your book summary');
 *   }
 * }
 * ```
 */
```

### generateToc
```typescript
/**
 * Generate table of contents from summary and question responses
 *
 * Uses AI to create a comprehensive table of contents based on:
 * - The book summary
 * - User responses to clarifying questions
 * - Target audience and genre
 *
 * The generated TOC includes main chapters and optional subchapters,
 * with descriptions and estimated page counts.
 *
 * @param bookId - Unique identifier for the book
 * @param questionResponses - Array of question/answer pairs
 * @returns Promise resolving to generated TOC structure
 *
 * @throws {Error} When generation fails
 *   - 400: Invalid request data or insufficient responses
 *   - 401: User is not authenticated
 *   - 403: User does not have access to this book
 *   - 404: Book not found
 *   - 422: Validation error (e.g., responses don't match questions)
 *   - 500: Server error or AI service unavailable
 *
 * @example
 * ```typescript
 * // Generate TOC from Q&A responses
 * const questionResponses = [
 *   { question: 'Who is your target audience?', answer: 'Beginners' },
 *   { question: 'What key topics will you cover?', answer: 'Basics, Advanced, Tips' }
 * ];
 *
 * const result = await bookClient.generateToc(bookId, questionResponses);
 *
 * console.log(`Generated ${result.chapters_count} chapters`);
 * console.log(`Estimated pages: ${result.toc.estimated_pages}`);
 * console.log(`Has subchapters: ${result.has_subchapters}`);
 *
 * result.toc.chapters.forEach(chapter => {
 *   console.log(`Chapter ${chapter.order}: ${chapter.title}`);
 *   console.log(`  Description: ${chapter.description}`);
 *
 *   if (chapter.subchapters.length > 0) {
 *     chapter.subchapters.forEach(sub => {
 *       console.log(`    ${sub.order}. ${sub.title}`);
 *     });
 *   }
 * });
 *
 * // Recommendation: Save generated TOC immediately
 * if (result.success) {
 *   await bookClient.updateToc(bookId, result.toc);
 * }
 * ```
 */
```

### getToc
```typescript
/**
 * Get current table of contents for a book
 *
 * Retrieves the book's TOC structure including all chapters,
 * subchapters, and metadata. Returns null if no TOC has been generated.
 *
 * @param bookId - Unique identifier for the book
 * @returns Promise resolving to TOC structure or null
 *
 * @throws {Error} When retrieval fails
 *   - 401: User is not authenticated
 *   - 403: User does not have access to this book
 *   - 404: Book not found
 *   - 500: Server error occurred
 *
 * @example
 * ```typescript
 * // Fetch TOC
 * const result = await bookClient.getToc(bookId);
 *
 * if (result.toc === null) {
 *   console.log('No TOC generated yet');
 * } else {
 *   console.log(`TOC has ${result.toc.total_chapters} chapters`);
 *   console.log(`Estimated pages: ${result.toc.estimated_pages}`);
 *
 *   // Display chapter structure
 *   result.toc.chapters.forEach(chapter => {
 *     console.log(`${chapter.order}. ${chapter.title} (Level ${chapter.level})`);
 *   });
 * }
 * ```
 */
```

### updateToc
```typescript
/**
 * Update table of contents for a book
 *
 * Replaces the entire TOC structure with the provided data.
 * This is a full replacement operation, not a patch.
 *
 * Use this after:
 * - AI generation to save the generated TOC
 * - Manual editing in the TOC management interface
 * - Reorganizing chapter structure
 *
 * @param bookId - Unique identifier for the book
 * @param toc - Complete TOC structure to save
 * @returns Promise resolving to updated TOC and success status
 *
 * @throws {Error} When update fails
 *   - 400: Invalid TOC structure
 *   - 401: User is not authenticated
 *   - 403: User does not have permission to edit this book
 *   - 404: Book not found
 *   - 422: Validation error (e.g., invalid chapter IDs, duplicate orders)
 *   - 500: Server error occurred
 *
 * @example
 * ```typescript
 * // Update TOC after generation
 * const generatedToc = await bookClient.generateToc(bookId, responses);
 * const result = await bookClient.updateToc(bookId, generatedToc.toc);
 *
 * if (result.success) {
 *   console.log('TOC saved successfully');
 * }
 *
 * // Update TOC with modifications
 * const currentToc = await bookClient.getToc(bookId);
 * if (currentToc.toc) {
 *   // Modify TOC structure
 *   currentToc.toc.chapters[0].title = 'Updated Chapter Title';
 *
 *   // Save changes
 *   await bookClient.updateToc(bookId, currentToc.toc);
 * }
 * ```
 */
```

## Summary Management Methods

### getBookSummary
```typescript
/**
 * Get the summary and revision history for a book
 *
 * Retrieves the current book summary along with optional revision history.
 * The summary is used for TOC generation and book planning.
 *
 * @param bookId - Unique identifier for the book
 * @returns Promise resolving to summary and history
 *
 * @throws {Error} When retrieval fails
 *   - 401: User is not authenticated
 *   - 403: User does not have access to this book
 *   - 404: Book not found
 *   - 500: Server error occurred
 *
 * @example
 * ```typescript
 * // Fetch summary
 * const result = await bookClient.getBookSummary(bookId);
 * console.log('Current summary:', result.summary);
 *
 * if (result.summary_history) {
 *   console.log(`${result.summary_history.length} previous versions`);
 * }
 *
 * // Check if summary exists
 * if (!result.summary || result.summary.trim().length === 0) {
 *   alert('Please add a book summary to continue');
 * }
 * ```
 */
```

### saveBookSummary
```typescript
/**
 * Save or update the summary for a book
 *
 * Updates the book's summary content. Previous versions are automatically
 * saved to the revision history. The new summary becomes the active version.
 *
 * @param bookId - Unique identifier for the book
 * @param summary - New summary content (max 5000 characters)
 * @returns Promise resolving to saved summary and success status
 *
 * @throws {Error} When save fails
 *   - 400: Invalid request data
 *   - 401: User is not authenticated
 *   - 403: User does not have permission to edit this book
 *   - 404: Book not found
 *   - 422: Validation error (e.g., summary too long)
 *   - 500: Server error occurred
 *
 * @example
 * ```typescript
 * // Save new summary
 * const summary = `This book explores the fundamentals of...`;
 * const result = await bookClient.saveBookSummary(bookId, summary);
 *
 * if (result.success) {
 *   console.log('Summary saved:', result.summary);
 * }
 *
 * // With validation
 * const maxLength = 5000;
 * if (summary.length > maxLength) {
 *   alert(`Summary too long. Max ${maxLength} characters.`);
 *   return;
 * }
 *
 * await bookClient.saveBookSummary(bookId, summary);
 * ```
 */
```

## Chapter Content Methods

### saveChapterContent
```typescript
/**
 * Save chapter content
 *
 * Updates the content for a specific chapter. Optionally updates
 * metadata (word count, reading time) automatically.
 *
 * ⚠️ **Auto-save considerations**: This method is called frequently
 * by auto-save. Backend handles debouncing and optimistic updates.
 *
 * @param bookId - Unique identifier for the book
 * @param chapterId - Unique identifier for the chapter
 * @param content - Chapter content (HTML from TipTap editor)
 * @param autoUpdateMetadata - Whether to recalculate metadata (default: true)
 * @returns Promise resolving to save result with metadata update status
 *
 * @throws {Error} When save fails
 *   - 400: Invalid request data
 *   - 401: User is not authenticated
 *   - 403: User does not have permission to edit this book
 *   - 404: Book or chapter not found
 *   - 422: Validation error
 *   - 500: Server error occurred
 *   - Network errors: Triggers localStorage backup in auto-save
 *
 * @example
 * ```typescript
 * // Manual save
 * const result = await bookClient.saveChapterContent(
 *   bookId,
 *   chapterId,
 *   editorContent
 * );
 *
 * console.log('Content saved:', result.success);
 * console.log('Metadata updated:', result.metadata_updated);
 *
 * // Auto-save with debounce
 * const debouncedSave = useCallback(
 *   debounce(async (content: string) => {
 *     try {
 *       await bookClient.saveChapterContent(bookId, chapterId, content);
 *       setLastSaved(new Date());
 *     } catch (error) {
 *       // Fallback to localStorage
 *       localStorage.setItem(`chapter-${chapterId}`, content);
 *       console.error('Save failed, using localStorage backup');
 *     }
 *   }, 3000),
 *   [bookId, chapterId]
 * );
 *
 * // Disable metadata update for performance
 * await bookClient.saveChapterContent(
 *   bookId,
 *   chapterId,
 *   content,
 *   false // Skip metadata calculation for fast auto-save
 * );
 * ```
 *
 * @see {@link frontend/src/components/editor/ChapterEditor.tsx} - Auto-save implementation
 */
```

### getChapterContent
```typescript
/**
 * Get chapter content with optional metadata
 *
 * Retrieves the content for a specific chapter, optionally including
 * metadata (word count, reading time, last modified) and tracking access.
 *
 * @param bookId - Unique identifier for the book
 * @param chapterId - Unique identifier for the chapter
 * @param includeMetadata - Whether to include metadata (default: true)
 * @param trackAccess - Whether to log this access for analytics (default: true)
 * @returns Promise resolving to chapter content and metadata
 *
 * @throws {Error} When retrieval fails
 *   - 401: User is not authenticated
 *   - 403: User does not have access to this book
 *   - 404: Book or chapter not found
 *   - 500: Server error occurred
 *
 * @example
 * ```typescript
 * // Fetch content with metadata
 * const result = await bookClient.getChapterContent(bookId, chapterId);
 *
 * console.log('Content:', result.content);
 * if (result.metadata) {
 *   console.log(`Word count: ${result.metadata.word_count}`);
 *   console.log(`Status: ${result.metadata.status}`);
 *   console.log(`Reading time: ${result.metadata.estimated_reading_time} min`);
 * }
 *
 * // Fetch without metadata for performance
 * const { content } = await bookClient.getChapterContent(
 *   bookId,
 *   chapterId,
 *   false, // Skip metadata
 *   false  // Skip access tracking
 * );
 *
 * // Load with localStorage fallback
 * try {
 *   const { content } = await bookClient.getChapterContent(bookId, chapterId);
 *   setEditorContent(content);
 * } catch (error) {
 *   // Check for local backup
 *   const backup = localStorage.getItem(`chapter-${chapterId}`);
 *   if (backup) {
 *     console.log('Using localStorage backup');
 *     setEditorContent(backup);
 *   }
 * }
 * ```
 */
```

Continue with complete documentation...


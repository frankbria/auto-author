/**
 * End-to-End System Test for Auto Author
 * 
 * This test validates the complete authoring workflow from book creation
 * through chapter draft generation, using real AI services.
 * 
 * Test Flow:
 * 1. Create a non-fiction book with title and summary
 * 2. Generate and answer book-level questions
 * 3. Generate Table of Contents
 * 4. Create Chapter 1
 * 5. Generate and answer chapter questions
 * 6. Generate chapter draft from answers
 * 
 * This is the gold standard test - if this passes, the core system is working.
 */

import { test, expect, Page } from '@playwright/test';

// Test configuration
const TEST_TIMEOUT = 300000; // 5 minutes for full E2E with AI calls
const AI_RESPONSE_TIMEOUT = 60000; // 1 minute for individual AI responses

// Test data
const TEST_BOOK = {
  title: 'The Psychology of Habit Formation: A Practical Guide',
  genre: 'Non-Fiction',
  targetAudience: 'Adults interested in personal development',
  description: 'A comprehensive guide to understanding how habits are formed in the brain and practical strategies for building positive habits and breaking negative ones. Based on neuroscience research and behavioral psychology.',
};

const BOOK_QUESTION_ANSWERS = {
  'target_audience': 'Adults aged 25-55 who are interested in personal development, self-improvement, and understanding the science behind behavior change. Includes professionals, parents, and students.',
  'key_takeaways': 'Readers will understand the neurological basis of habits, learn the habit loop framework, discover evidence-based techniques for habit formation, and gain practical tools for implementing lasting behavioral changes.',
  'unique_perspective': 'This book combines cutting-edge neuroscience research with practical, actionable strategies. Unlike other habit books, it provides a deep understanding of the brain mechanisms involved while remaining accessible to general readers.',
};

const CHAPTER_QUESTION_ANSWERS = {
  'main_points': 'This chapter will introduce the concept of habits, explain why they are crucial for daily life, present the basic neuroscience of habit formation, and preview the book\'s framework for understanding and changing habits.',
  'opening_hook': 'We will open with a relatable scenario of someone trying to establish a morning exercise routine, showing the internal struggle between intention and automatic behavior, immediately connecting readers to the topic.',
  'key_examples': 'Examples will include morning routines, driving routes, smartphone checking behavior, and eating patterns. Each example will illustrate different aspects of automatic behavior and its impact on our lives.',
};

test.describe('Auto Author E2E System Test', () => {
  test.setTimeout(TEST_TIMEOUT);

  test('Complete authoring workflow from book creation to chapter draft', async ({ page }) => {
    // Step 1: Navigate to the application and login
    await test.step('Login to the application', async () => {
      await page.goto('/');
      
      // Handle Clerk authentication - adjust based on your auth setup
      // For testing, you might need to use a test account or mock auth
      await page.waitForLoadState('networkidle');
      
      // If using Clerk dev mode, it might auto-login
      // Otherwise, add login steps here
    });

    // Step 2: Create a new book
    const bookId = await test.step('Create a new non-fiction book', async () => {
      await page.goto('/dashboard');
      await page.getByRole('button', { name: /create new book/i }).click();
      
      // Fill in book details
      await page.getByLabel(/title/i).fill(TEST_BOOK.title);
      await page.getByLabel(/genre/i).selectOption(TEST_BOOK.genre);
      await page.getByLabel(/target audience/i).fill(TEST_BOOK.targetAudience);
      await page.getByLabel(/description/i).fill(TEST_BOOK.description);
      
      // Submit the form
      await page.getByRole('button', { name: /create book/i }).click();
      
      // Wait for redirect to book page
      await page.waitForURL(/\/dashboard\/books\/[^\/]+$/);
      
      // Extract book ID from URL
      const url = page.url();
      const bookId = url.match(/books\/([^\/]+)$/)?.[1];
      expect(bookId).toBeTruthy();
      
      return bookId!;
    });

    // Step 3: Generate book-level questions
    await test.step('Generate and answer book-level questions', async () => {
      // Click on generate questions or similar button
      await page.getByRole('button', { name: /generate book outline|start book planning/i }).click();
      
      // Wait for AI to generate questions
      await page.waitForSelector('[data-testid="book-questions"]', { 
        timeout: AI_RESPONSE_TIMEOUT 
      });
      
      // Answer the questions
      const questions = await page.$$('[data-testid="question-input"]');
      expect(questions.length).toBeGreaterThan(0);
      
      // Fill in answers based on question content
      for (const questionInput of questions) {
        const questionText = await questionInput.getAttribute('data-question-type') || 
                           await questionInput.getAttribute('name');
        
        if (questionText?.includes('audience')) {
          await questionInput.fill(BOOK_QUESTION_ANSWERS.target_audience);
        } else if (questionText?.includes('takeaway') || questionText?.includes('learn')) {
          await questionInput.fill(BOOK_QUESTION_ANSWERS.key_takeaways);
        } else if (questionText?.includes('unique') || questionText?.includes('different')) {
          await questionInput.fill(BOOK_QUESTION_ANSWERS.unique_perspective);
        }
      }
      
      // Submit answers
      await page.getByRole('button', { name: /submit|continue|next/i }).click();
    });

    // Step 4: Generate Table of Contents
    await test.step('Generate Table of Contents using AI', async () => {
      // Wait for TOC generation interface
      await page.waitForSelector('[data-testid="toc-generator"]', {
        timeout: AI_RESPONSE_TIMEOUT
      });
      
      // Click generate TOC button
      await page.getByRole('button', { name: /generate table of contents|create chapters/i }).click();
      
      // Wait for AI response
      await page.waitForSelector('[data-testid="chapter-list"]', {
        timeout: AI_RESPONSE_TIMEOUT
      });
      
      // Verify chapters were created
      const chapters = await page.$$('[data-testid="chapter-item"]');
      expect(chapters.length).toBeGreaterThan(0);
      
      // Save the TOC
      await page.getByRole('button', { name: /save|confirm|accept/i }).click();
    });

    // Step 5: Navigate to Chapter 1
    await test.step('Navigate to Chapter 1', async () => {
      // Click on the first chapter or navigate to chapters tab
      await page.getByRole('tab', { name: /chapters/i }).click();
      
      // Click on Chapter 1
      await page.getByText(/chapter 1/i).first().click();
      
      // Wait for chapter interface to load
      await page.waitForSelector('[data-testid="chapter-editor"]');
    });

    // Step 6: Generate chapter questions
    await test.step('Generate and answer chapter questions', async () => {
      // Click on generate questions for the chapter
      await page.getByRole('button', { name: /generate questions|interview questions/i }).click();
      
      // Wait for AI to generate questions
      await page.waitForSelector('[data-testid="chapter-questions"]', {
        timeout: AI_RESPONSE_TIMEOUT
      });
      
      // Answer chapter questions
      const chapterQuestions = await page.$$('[data-testid="chapter-question-input"]');
      expect(chapterQuestions.length).toBeGreaterThan(0);
      
      for (const questionInput of chapterQuestions) {
        const questionText = await questionInput.getAttribute('data-question-type') ||
                           await questionInput.textContent();
        
        if (questionText?.includes('main points') || questionText?.includes('cover')) {
          await questionInput.fill(CHAPTER_QUESTION_ANSWERS.main_points);
        } else if (questionText?.includes('open') || questionText?.includes('hook')) {
          await questionInput.fill(CHAPTER_QUESTION_ANSWERS.opening_hook);
        } else if (questionText?.includes('example') || questionText?.includes('illustrate')) {
          await questionInput.fill(CHAPTER_QUESTION_ANSWERS.key_examples);
        }
      }
      
      // Mark questions as complete
      await page.getByRole('button', { name: /complete|done|save answers/i }).click();
    });

    // Step 7: Generate chapter draft
    const draftContent = await test.step('Generate chapter draft from answers', async () => {
      // Click generate draft button
      await page.getByRole('button', { name: /generate draft|create draft|ai draft/i }).click();
      
      // Wait for AI to generate the draft
      await page.waitForSelector('[data-testid="draft-content"]', {
        timeout: AI_RESPONSE_TIMEOUT
      });
      
      // Verify draft was generated
      const draftElement = await page.locator('[data-testid="draft-content"]');
      const draftText = await draftElement.textContent();
      
      expect(draftText).toBeTruthy();
      expect(draftText!.length).toBeGreaterThan(500); // Should be substantial content
      
      // Check that draft relates to our topic
      expect(draftText!.toLowerCase()).toContain('habit');
      
      return draftText!;
    });

    // Step 8: Verify the complete workflow
    await test.step('Verify complete system functionality', async () => {
      // Verify we have a book
      await page.goto(`/dashboard/books/${bookId}`);
      await expect(page.getByText(TEST_BOOK.title)).toBeVisible();
      
      // Verify we have chapters
      const chapterCount = await page.locator('[data-testid="chapter-tab"]').count();
      expect(chapterCount).toBeGreaterThan(0);
      
      // Verify we have draft content
      expect(draftContent).toContain('habit');
      expect(draftContent.length).toBeGreaterThan(500);
      
      console.log('✅ E2E System Test Passed!');
      console.log(`📚 Book Created: ${TEST_BOOK.title}`);
      console.log(`📑 Chapters Generated: ${chapterCount}`);
      console.log(`📝 Draft Length: ${draftContent.length} characters`);
    });

    // Optional: Cleanup
    await test.step('Cleanup test data', async () => {
      // Optionally delete the test book to keep the system clean
      // await page.goto(`/dashboard/books/${bookId}/settings`);
      // await page.getByRole('button', { name: /delete book/i }).click();
      // await page.getByRole('button', { name: /confirm/i }).click();
    });
  });
});

/**
 * Additional granular tests can be added here for specific workflows:
 * - Test PDF export of the generated content
 * - Test editing and saving changes
 * - Test voice input functionality
 * - Test different book genres
 * - Test error recovery scenarios
 */
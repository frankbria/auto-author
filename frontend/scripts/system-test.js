#!/usr/bin/env node

/**
 * Auto Author System Test Script
 * 
 * This script tests the complete authoring workflow from book creation
 * through chapter draft generation, using real API services.
 * 
 * Usage: node scripts/system-test.js [--cleanup]
 * 
 * Options:
 *   --cleanup    Delete test data after completion
 */

const axios = require('axios');
const colors = require('colors');

// Configuration
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api/v1';
const API_TOKEN = process.env.API_TOKEN || ''; // Add your auth token
const CLEANUP = process.argv.includes('--cleanup');

// Test data
const TEST_BOOK = {
  title: `System Test Book - ${new Date().toISOString().split('T')[0]}`,
  author_name: 'System Test',
  genre: 'Non-Fiction',
  target_audience: 'Adults interested in personal development',
  description: 'A test book for validating the complete Auto Author system workflow.',
  language: 'English',
  estimated_word_count: 50000,
};

// API client setup
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${API_TOKEN}`,
  },
  timeout: 60000, // 1 minute timeout for AI calls
});

// Utility functions
const log = {
  info: (msg) => console.log(colors.blue(`ℹ️  ${msg}`)),
  success: (msg) => console.log(colors.green(`✅ ${msg}`)),
  error: (msg) => console.log(colors.red(`❌ ${msg}`)),
  step: (msg) => console.log(colors.yellow(`\n🔸 ${msg}`)),
};

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Test functions
async function createBook() {
  log.step('Creating book...');
  const response = await api.post('/books', TEST_BOOK);
  const book = response.data;
  log.success(`Book created: ${book.title} (ID: ${book.id})`);
  return book;
}

async function generateBookQuestions(bookId) {
  log.step('Generating book summary questions...');
  const response = await api.post(`/books/${bookId}/summary-questions`);
  const questions = response.data.questions;
  log.success(`Generated ${questions.length} summary questions`);
  return questions;
}

async function answerBookQuestions(bookId, questions) {
  log.step('Answering book summary questions...');
  const answers = questions.map((q, index) => ({
    question_id: q.id,
    question_text: q.question_text,
    answer: getBookAnswer(q.question_text, index),
  }));
  
  const response = await api.post(`/books/${bookId}/summary-answers`, { answers });
  log.success('Summary answers submitted');
  return response.data;
}

async function generateTOC(bookId) {
  log.step('Generating Table of Contents...');
  const response = await api.post(`/books/${bookId}/generate-toc`, {
    chapter_count: 10,
    include_introduction: true,
    include_conclusion: true,
  });
  const toc = response.data;
  log.success(`Generated TOC with ${toc.chapters.length} chapters`);
  return toc;
}

async function createChapters(bookId, chapters) {
  log.step('Creating chapters from TOC...');
  const response = await api.post(`/books/${bookId}/chapters/bulk`, { chapters });
  const createdChapters = response.data;
  log.success(`Created ${createdChapters.length} chapters`);
  return createdChapters;
}

async function generateChapterQuestions(bookId, chapterId) {
  log.step('Generating questions for Chapter 1...');
  const response = await api.post(`/books/${bookId}/chapters/${chapterId}/questions/generate`, {
    count: 5,
    difficulty: 'mixed',
  });
  const questions = response.data.questions;
  log.success(`Generated ${questions.length} chapter questions`);
  return questions;
}

async function answerChapterQuestions(bookId, chapterId, questions) {
  log.step('Answering chapter questions...');
  
  for (const question of questions) {
    const answer = getChapterAnswer(question.question_text);
    await api.post(`/books/${bookId}/chapters/${chapterId}/questions/${question.id}/response`, {
      response_text: answer,
      status: 'completed',
    });
  }
  
  log.success('All chapter questions answered');
}

async function generateChapterDraft(bookId, chapterId) {
  log.step('Generating chapter draft from answers...');
  const response = await api.post(`/books/${bookId}/chapters/${chapterId}/generate-draft`, {
    writing_style: 'educational',
    target_word_count: 2000,
  });
  const draft = response.data.draft;
  log.success(`Generated draft with ${draft.length} characters`);
  return draft;
}

async function saveChapterContent(chapterId, content) {
  log.step('Saving draft to chapter...');
  await api.patch(`/chapters/${chapterId}`, {
    content: content,
    status: 'draft',
  });
  log.success('Draft saved successfully');
}

async function verifySystem(bookId, chapterId) {
  log.step('Verifying complete workflow...');
  
  // Verify book
  const bookResponse = await api.get(`/books/${bookId}`);
  const book = bookResponse.data;
  
  // Verify chapters
  const chaptersResponse = await api.get(`/books/${bookId}/chapters`);
  const chapters = chaptersResponse.data;
  
  // Verify content
  const chapterResponse = await api.get(`/chapters/${chapterId}`);
  const chapter = chapterResponse.data;
  
  log.info(`Book: ${book.title}`);
  log.info(`Chapters: ${chapters.length}`);
  log.info(`Draft Length: ${chapter.content?.length || 0} characters`);
  
  if (chapter.content && chapter.content.length > 500) {
    log.success('System verification passed!');
    return true;
  } else {
    throw new Error('Chapter content not generated properly');
  }
}

async function cleanup(bookId) {
  if (CLEANUP && bookId) {
    log.step('Cleaning up test data...');
    try {
      await api.delete(`/books/${bookId}`);
      log.success('Test data cleaned up');
    } catch (error) {
      log.error(`Failed to cleanup: ${error.message}`);
    }
  }
}

// Helper functions
function getBookAnswer(questionText, index) {
  const answers = [
    'Adults aged 25-55 interested in personal development and understanding behavior change',
    'Readers will understand the neurological basis of habits and gain practical tools for change',
    'This book combines neuroscience research with actionable strategies for lasting change',
  ];
  return answers[index] || 'This book provides comprehensive guidance on habit formation';
}

function getChapterAnswer(questionText) {
  const lowerText = questionText.toLowerCase();
  
  if (lowerText.includes('main points') || lowerText.includes('cover')) {
    return 'Introduce habits concept, explain neuroscience basis, preview book framework';
  } else if (lowerText.includes('open') || lowerText.includes('hook')) {
    return 'Open with relatable morning routine scenario showing habit struggles';
  } else if (lowerText.includes('example')) {
    return 'Morning routines, driving routes, smartphone checking, eating patterns';
  } else {
    return 'This chapter establishes the foundation for understanding habit formation';
  }
}

// Main test execution
async function runSystemTest() {
  console.log(colors.cyan('\n🚀 Auto Author System Test Starting...\n'));
  
  let bookId, chapterId;
  const startTime = Date.now();
  
  try {
    // Execute test workflow
    const book = await createBook();
    bookId = book.id;
    
    const bookQuestions = await generateBookQuestions(bookId);
    await answerBookQuestions(bookId, bookQuestions);
    
    const toc = await generateTOC(bookId);
    const chapters = await createChapters(bookId, toc.chapters);
    chapterId = chapters[0].id;
    
    const chapterQuestions = await generateChapterQuestions(bookId, chapterId);
    await answerChapterQuestions(bookId, chapterId, chapterQuestions);
    
    const draft = await generateChapterDraft(bookId, chapterId);
    await saveChapterContent(chapterId, draft);
    
    await verifySystem(bookId, chapterId);
    
    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    console.log(colors.green(`\n✅ SYSTEM TEST PASSED in ${duration} seconds!\n`));
    
  } catch (error) {
    console.error(colors.red('\n❌ SYSTEM TEST FAILED!\n'));
    console.error(colors.red(error.message));
    if (error.response) {
      console.error(colors.red('API Error:', error.response.data));
    }
    process.exit(1);
  } finally {
    await cleanup(bookId);
  }
}

// Check for required environment
if (!API_TOKEN && API_BASE_URL.includes('localhost')) {
  log.error('Warning: No API_TOKEN set. This may fail if authentication is required.');
}

// Run the test
runSystemTest().catch(console.error);
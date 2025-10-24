/**
 * Test Data Fixtures
 *
 * Static test data for deployment testing, sourced from
 * DEPLOYMENT-TESTING-CHECKLIST.md
 */

export interface BookData {
  title: string;
  description: string;
  genre: string;
  targetAudience: string;
}

export interface SummaryData {
  content: string;
  minLength: number;
  maxLength: number;
  expectedCharCount: number;
}

export interface TOCQuestion {
  question: string;
  answer: string;
}

export interface ChapterQAData {
  question: string;
  answer: string;
}

/**
 * Test book data - Sustainable Urban Gardening
 */
export const TEST_BOOK: BookData = {
  title: "Sustainable Urban Gardening: A Practical Guide",
  description: "A comprehensive guide for city dwellers to grow fresh produce in limited spaces",
  genre: "business",
  targetAudience: "Urban residents interested in growing their own food in limited spaces"
};

/**
 * Book summary test data (558 characters)
 */
export const TEST_SUMMARY: SummaryData = {
  content: `This practical guide teaches urban dwellers how to create productive gardens in small spaces. Topics include container gardening basics, vertical growing techniques for balconies and patios, composting in urban environments, seasonal planning for year-round harvests, and selecting the best vegetables and herbs for limited space. Readers will learn water-efficient irrigation methods, organic pest control strategies, and how to maximize yields in apartments and small yards. The book includes detailed growing calendars, troubleshooting guides, and case studies from successful urban gardeners.`,
  minLength: 30,
  maxLength: 2000,
  expectedCharCount: 558
};

/**
 * TOC wizard clarifying questions and answers
 */
export const TOC_QUESTIONS: TOCQuestion[] = [
  {
    question: "Main Topics",
    answer: "This book covers container gardening, vertical growing, composting, seasonal planning, and space-efficient techniques for urban environments."
  },
  {
    question: "Target Readers",
    answer: "Beginners with no gardening experience living in apartments or homes with limited outdoor space who want to grow fresh food."
  },
  {
    question: "Key Takeaways",
    answer: "Readers will learn that productive gardening is possible in small spaces, understand basic techniques, and feel motivated to start their own urban garden."
  },
  {
    question: "Scope",
    answer: "The book focuses on vegetables, herbs, and small fruits suitable for containers and small urban spaces, not large-scale farming."
  },
  {
    question: "Unique Approach",
    answer: "Emphasizes practical, budget-friendly solutions using recycled materials and minimal space, with real-world examples from city gardeners."
  }
];

/**
 * Chapter Q&A test data for AI draft generation
 */
export const CHAPTER_QA_DATA: ChapterQAData[] = [
  {
    question: "What are the main topics for this chapter?",
    answer: "Introduction to container gardening, choosing the right containers, soil selection, and drainage requirements for successful urban gardens."
  },
  {
    question: "What should readers learn by the end?",
    answer: "Readers will understand how to select appropriate containers, prepare proper soil mixes, and ensure adequate drainage for healthy plant growth in limited spaces."
  },
  {
    question: "What examples or case studies should be included?",
    answer: "Show examples of different container types (terracotta, plastic, fabric), a recipe for DIY potting mix, and a troubleshooting guide for common drainage problems."
  }
];

/**
 * Field validation constraints
 */
export const FIELD_CONSTRAINTS = {
  bookTitle: { min: 1, max: 100 },
  description: { max: 5000 },
  targetAudience: { max: 100 },
  summary: { min: 30, max: 2000 },
  chapterResponse: { min: 50, max: 500 }
};

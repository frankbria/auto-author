import { ChapterStatus } from './chapter-tabs';

// Types for TOC generation wizard and components

export interface TocChapter {
  id: string;
  title: string;
  description: string;
  level: number;
  order: number;
  subchapters: TocSubchapter[];

  // NEW: Tab functionality fields
  status: ChapterStatus;
  word_count: number;
  last_modified?: string;
  estimated_reading_time: number;
  content_id?: string;
}

export interface TocSubchapter {
  id: string;
  title: string;
  description: string;
  level: number;
  order: number;
}

export interface TocData {
  chapters: TocChapter[];
  total_chapters: number;
  estimated_pages: number;
  structure_notes: string;
}

export interface TocReadiness {
  is_ready_for_toc: boolean;
  confidence_score: number;
  analysis: string;
  suggestions: string[];
  word_count: number;
  character_count: number;
  meets_minimum_requirements: boolean;
}

export interface QuestionResponse {
  question: string;
  answer: string;
}

export interface TocGenerationResult {
  toc: TocData;
  success: boolean;
  chapters_count: number;
  has_subchapters: boolean;
}

export enum WizardStep {
  CHECKING_READINESS = 'checking_readiness',
  NOT_READY = 'not_ready',
  ASKING_QUESTIONS = 'asking_questions',
  GENERATING = 'generating',
  REVIEW = 'review',
  ERROR = 'error'
}

export interface WizardState {
  step: WizardStep;
  readiness?: TocReadiness;
  questions?: string[];
  questionResponses: QuestionResponse[];
  generatedToc?: TocGenerationResult;
  error?: string;
  isLoading: boolean;
}

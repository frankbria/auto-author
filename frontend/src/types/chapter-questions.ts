export enum QuestionType {
  CHARACTER = "character",
  PLOT = "plot",
  SETTING = "setting",
  THEME = "theme",
  RESEARCH = "research"
}

export enum QuestionDifficulty {
  EASY = "easy",
  MEDIUM = "medium",
  HARD = "hard"
}

export enum ResponseStatus {
  DRAFT = "draft",
  COMPLETED = "completed"
}

export interface QuestionMetadata {
  suggested_response_length: string;
  help_text?: string;
  examples?: string[];
}

export interface Question {
  id: string;
  chapter_id: string;
  question_text: string;
  question_type: QuestionType;
  difficulty: QuestionDifficulty;
  category: string;
  order: number;
  generated_at: string;
  metadata: QuestionMetadata;
  has_response?: boolean;
  response_status?: ResponseStatus;
}

export interface QuestionResponse {
  id: string;
  question_id: string;
  response_text: string;
  word_count: number;
  status: ResponseStatus;
  created_at: string;
  updated_at: string;
  last_edited_at: string;
  metadata: {
    edit_history: Array<{
      timestamp: string;
      word_count: number;
    }>;
  };
}

export interface QuestionProgressResponse {
  total: number;
  completed: number;
  in_progress: number;
  progress: number; // 0.0 to 1.0
  status: "not-started" | "in-progress" | "completed";
}

export interface GenerateQuestionsRequest {
  count?: number; // Default: 10
  difficulty?: QuestionDifficulty;
  focus?: QuestionType[];
}

export interface GenerateQuestionsResponse {
  questions: Question[];
  generation_id: string;
  total: number;
}

export interface QuestionListResponse {
  questions: Question[];
  total: number;
  page: number;
  pages: number;
}

export interface QuestionResponseRequest {
  response_text: string;
  status: ResponseStatus;
}

export interface QuestionRatingRequest {
  rating: number; // 1-5
  feedback?: string;
}

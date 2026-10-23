import { QuestionType } from '@/types/chapter-questions';

// #1051: the stored QuestionType values (persisted on questions, used by the backend templates)
// stay as they are; only these displayed labels are non-fiction. Wording follows question_templates.py (#835).
export const FOCUS_OPTIONS: { type: QuestionType; label: string; description: string }[] = [
  { type: QuestionType.CHARACTER, label: 'People', description: 'The reader this chapter is for and the people whose experience or work it draws on' },
  { type: QuestionType.PLOT, label: 'Structure', description: 'The main point, the order of your ideas and how they reach the conclusion' },
  { type: QuestionType.SETTING, label: 'Context', description: 'The situation the chapter applies to and the background a reader needs' },
  { type: QuestionType.THEME, label: 'Message', description: 'The idea a reader should take away and how it serves the book\'s argument' },
  { type: QuestionType.RESEARCH, label: 'Evidence', description: 'Sources and facts that need checking, and terms that need explaining' },
];

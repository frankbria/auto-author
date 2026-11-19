/**
 * @jest-environment node
 */
import { DEFAULT_PLANS, displayAmount, freeTrialFeatures, generationWindows, proFeatures } from '../plans';

const free = DEFAULT_PLANS.plans.free;
const pro = DEFAULT_PLANS.plans.pro;

describe('plans copy', () => {
  it('defaults match the backend settings and the adopted price', () => {
    expect(free).toEqual({ daily: null, monthly: null, total: 30, draft_chapters: 1, export: false });
    expect(pro).toEqual({ daily: 50, monthly: 500, total: null, draft_chapters: null, export: true });
    expect(DEFAULT_PLANS.pro_price).toEqual({ amount: '$49', period: 'month' });
  });

  it('drops a whole-dollar amount\'s cents and leaves others alone', () => {
    expect(displayAmount('$49.00')).toBe('$49');
    expect(displayAmount('$1,049.00')).toBe('$1,049');
    expect(displayAmount('$49.50')).toBe('$49.50');
    expect(displayAmount('€49.00')).toBe('€49.00');
  });

  it('words each generation window', () => {
    expect(generationWindows(pro)).toBe('50 AI generations a day (500 a month)');
    expect(generationWindows({ ...pro, monthly: null })).toBe('50 AI generations a day');
    expect(generationWindows({ ...pro, daily: null })).toBe('500 AI generations a month');
    expect(generationWindows({ ...pro, daily: null, monthly: null })).toBe('Unlimited AI generations');
  });

  it('describes the trial as one chapter with a total that does not reset and no export', () => {
    expect(freeTrialFeatures(free)).toEqual([
      'A book summary, typed or dictated',
      'An AI table of contents you edit',
      "One chapter's interview questions and AI draft",
      'The full editor',
      "30 AI generations in total, which don't reset",
      'No export',
    ]);
  });

  it('follows changed trial settings', () => {
    const lines = freeTrialFeatures({ ...free, total: 1, draft_chapters: 2, export: true });
    expect(lines).toContain('Interview questions and AI drafts for 2 chapters');
    expect(lines).toContain("One AI generation in total, which don't reset");
    expect(lines).toContain('Export to PDF, DOCX, EPUB and Markdown');
    expect(freeTrialFeatures({ ...free, total: null, draft_chapters: null, daily: 5 })).toContain(
      '5 AI generations a day'
    );
  });

  it('describes Pro', () => {
    expect(proFeatures(pro)).toEqual([
      'Interview questions and AI drafts for every chapter',
      'The full editor, with AI style changes',
      '50 AI generations a day (500 a month)',
      'Export to PDF, DOCX, EPUB and Markdown',
      'Cancel anytime',
    ]);
    expect(proFeatures({ ...pro, export: false, draft_chapters: 3 })).toEqual([
      'Interview questions and AI drafts for 3 chapters',
      'The full editor, with AI style changes',
      '50 AI generations a day (500 a month)',
      'Cancel anytime',
    ]);
  });
});

import { QuestionType } from '@/types/chapter-questions';
import { FOCUS_OPTIONS } from '@/lib/questionFocus';

describe('FOCUS_OPTIONS (#1051)', () => {
  it('covers every stored QuestionType exactly once', () => {
    expect(FOCUS_OPTIONS.map((o) => o.type).sort()).toEqual(Object.values(QuestionType).sort());
  });

  it.each(FOCUS_OPTIONS)('$type has non-fiction wording', ({ label, description }) => {
    expect(label.length).toBeGreaterThan(0);
    expect(description.length).toBeGreaterThan(0);
    expect(`${label} ${description}`).not.toMatch(/character|plot|setting/i);
  });
});

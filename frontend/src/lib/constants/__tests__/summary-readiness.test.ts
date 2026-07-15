import {
  SUMMARY_MIN_WORDS,
  SUMMARY_MIN_CHARACTERS,
  SUMMARY_MAX_CHARACTERS,
  countSummaryWords,
  getSummaryReadinessError,
} from '../summary-readiness';

/** Build a summary with `words` words and at least `minChars` characters. */
const summaryOf = (words: number, wordLength = 6) =>
  Array.from({ length: words }, () => 'a'.repeat(wordLength)).join(' ');

describe('summary-readiness constants', () => {
  it('mirrors the backend gate exactly (books.py:1150 / ai_service.py:483)', () => {
    expect(SUMMARY_MIN_WORDS).toBe(30);
    expect(SUMMARY_MIN_CHARACTERS).toBe(150);
    expect(SUMMARY_MAX_CHARACTERS).toBe(2000);
  });
});

describe('countSummaryWords — parity with Python str.split()', () => {
  it('counts single-space-separated words', () => {
    expect(countSummaryWords('one two three')).toBe(3);
  });

  it('collapses runs of whitespace like str.split()', () => {
    expect(countSummaryWords('one   two\t\tthree\n\nfour')).toBe(4);
  });

  it('ignores leading and trailing whitespace like str.split()', () => {
    expect(countSummaryWords('  one two  ')).toBe(2);
  });

  it('returns 0 for empty and whitespace-only input', () => {
    expect(countSummaryWords('')).toBe(0);
    expect(countSummaryWords('   \n\t ')).toBe(0);
  });
});

describe('getSummaryReadinessError', () => {
  it('asks for a summary when empty', () => {
    expect(getSummaryReadinessError('')).toBe('Please provide a summary of your book.');
    expect(getSummaryReadinessError('   ')).toBe('Please provide a summary of your book.');
  });

  it('rejects a summary one word under the minimum', () => {
    // 29 long words: comfortably over the char minimum, so words is the sole failure.
    const text = summaryOf(SUMMARY_MIN_WORDS - 1, 10);
    expect(text.length).toBeGreaterThanOrEqual(SUMMARY_MIN_CHARACTERS);
    expect(getSummaryReadinessError(text)).toMatch(/30 words/);
  });

  it('rejects a summary one character under the minimum even with enough words', () => {
    // 30+ short words but under 150 characters — the case that silently passed the
    // old MIN_SUMMARY_LENGTH=30 char gate and then bounced at the wizard.
    const text = Array.from({ length: 40 }, () => 'ab').join(' ');
    expect(countSummaryWords(text)).toBeGreaterThanOrEqual(SUMMARY_MIN_WORDS);
    expect(text.length).toBeLessThan(SUMMARY_MIN_CHARACTERS);
    expect(getSummaryReadinessError(text)).toMatch(/150 characters/);
  });

  it('accepts a summary at exactly both minimums', () => {
    const text = summaryOf(SUMMARY_MIN_WORDS, 6); // 30 words, 209 chars
    expect(countSummaryWords(text)).toBe(SUMMARY_MIN_WORDS);
    expect(text.length).toBeGreaterThanOrEqual(SUMMARY_MIN_CHARACTERS);
    expect(getSummaryReadinessError(text)).toBe('');
  });

  it('rejects a summary over the maximum length', () => {
    // Must clear the word minimum first, or it fails on words rather than length.
    const text = summaryOf(400, 5); // 400 words / 2399 chars
    expect(countSummaryWords(text)).toBeGreaterThanOrEqual(SUMMARY_MIN_WORDS);
    expect(text.length).toBeGreaterThan(SUMMARY_MAX_CHARACTERS);
    expect(getSummaryReadinessError(text)).toMatch(/at most 2000 characters/);
  });

  it('accepts a summary at exactly the maximum length', () => {
    const text = summaryOf(400, 5).slice(0, SUMMARY_MAX_CHARACTERS);
    expect(text.length).toBe(SUMMARY_MAX_CHARACTERS);
    expect(getSummaryReadinessError(text)).toBe('');
  });

  it('still rejects offensive language and non-English text', () => {
    const long = summaryOf(SUMMARY_MIN_WORDS, 6);
    expect(getSummaryReadinessError(`${long} shit`)).toMatch(/inappropriate/i);
    expect(getSummaryReadinessError(`${long} привет`)).toMatch(/English/i);
  });

  it('accepts every summary the backend gate accepts (no client-side false rejection)', () => {
    // The whole bug class: client and server must agree at the boundary.
    const backendAccepts = (t: string) =>
      countSummaryWords(t) >= SUMMARY_MIN_WORDS && t.length >= SUMMARY_MIN_CHARACTERS;
    const cases = [
      summaryOf(30, 6),
      summaryOf(31, 4) + ' ' + 'x'.repeat(40),
      '  ' + summaryOf(35, 5) + '  ',
      summaryOf(30, 6).replace(/ /g, '\n'),
    ];
    for (const text of cases) {
      expect(backendAccepts(text)).toBe(true);
      expect(getSummaryReadinessError(text)).toBe('');
    }
  });
});

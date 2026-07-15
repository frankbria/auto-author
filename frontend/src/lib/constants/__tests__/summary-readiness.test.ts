import {
  SUMMARY_MIN_WORDS,
  SUMMARY_MIN_CHARACTERS,
  SUMMARY_MAX_CHARACTERS,
  countSummaryWords,
  countSummaryCharacters,
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
    // Each of these is 2 words to Python's split(); a naive split(' ') miscounts
    // the double-space case as 3, which is why this asserts per-case.
    expect(countSummaryWords('one  two')).toBe(2);
    expect(countSummaryWords('one\ttwo')).toBe(2);
    expect(countSummaryWords('one\ntwo')).toBe(2);
    expect(countSummaryWords('one   two\t\tthree\n\nfour')).toBe(4);
  });

  it('ignores leading and trailing whitespace like str.split()', () => {
    expect(countSummaryWords('  one two  ')).toBe(2);
  });

  it('returns 0 for empty and whitespace-only input', () => {
    expect(countSummaryWords('')).toBe(0);
    expect(countSummaryWords('   \n\t ')).toBe(0);
  });

  // JS /\s/ and Python str.split() disagree on two sets of characters. Both
  // divergences shift the count away from the backend's len(summary.split()).
  // Expected values below were produced by running the real Python:
  //   len("word1\x85word2".split()) == 2 ; len("word1﻿word2".split()) == 1

  it.each([
    ['\\x1c', '\x1c'],
    ['\\x1d', '\x1d'],
    ['\\x1e', '\x1e'],
    ['\\x1f', '\x1f'],
    ['\\x85 (NEL)', '\x85'],
  ])('splits on %s like Python (JS /\\s/ does not)', (_label, ch) => {
    expect(countSummaryWords(`word1${ch}word2`)).toBe(2);
  });

  it('does not split on \\ufeff (BOM) — Python does not treat it as whitespace', () => {
    // The regression that would recreate the #218 dead-end: counting this as 2
    // words client-side while the backend counts 1.
    expect(countSummaryWords('word1﻿word2')).toBe(1);
  });

  it('agrees with Python on the exotic whitespace it does share', () => {
    expect(countSummaryWords('one two')).toBe(2); // NBSP
    expect(countSummaryWords('one　two')).toBe(2); // ideographic space
    expect(countSummaryWords('one two')).toBe(2); // line separator
    expect(countSummaryWords('one two')).toBe(2); // four-per-em space
  });
});

describe('countSummaryCharacters — parity with Python len()', () => {
  it('counts a plain ASCII string like len()', () => {
    expect(countSummaryCharacters('hello')).toBe(5);
  });

  it('counts non-BMP characters once, as Python does (not as 2 UTF-16 units)', () => {
    // Verified against the real runtime: len('👍' * 100) == 100, while
    // '👍'.repeat(100).length === 200 in JS.
    expect(countSummaryCharacters('👍'.repeat(100))).toBe(100);
    expect('👍'.repeat(100).length).toBe(200); // documents the trap being avoided
  });

  it('does not let an emoji summary pass a gate the backend would fail', () => {
    // 100 emoji reads as 200 chars to String.length -> would clear the 150 gate
    // client-side and then be rejected by the backend's len() == 100.
    const text = `${summaryOf(SUMMARY_MIN_WORDS, 1)} ${'👍'.repeat(60)}`;
    const backendChars = countSummaryCharacters(text);
    if (backendChars < SUMMARY_MIN_CHARACTERS) {
      expect(getSummaryReadinessError(text)).toMatch(/at least 150 characters/);
    }
    expect(backendChars).toBeLessThan(text.length);
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

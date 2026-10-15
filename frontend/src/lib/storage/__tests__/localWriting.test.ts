/**
 * Each storage prefix clearLocalWriting removes still names a key the app writes (#855).
 *
 * A key renamed where it is written, and not here, would survive account
 * deletion with nothing failing.
 * shortcut: this catches a renamed key, not a new one; a new per-user key has to
 * be added to the prefix lists by hand.
 */
import { readFileSync } from 'fs';
import { join } from 'path';
import { FRONTEND_ROOT, shippedSources } from '@/__tests__/theme/helpers/sources';
import { LOCAL_PREFIXES, SESSION_PREFIXES, clearLocalWriting } from '../localWriting';

const THIS_MODULE = 'src/lib/storage/localWriting.ts';
const shipped = shippedSources()
  .filter((path) => path !== THIS_MODULE)
  .map((path) => readFileSync(join(FRONTEND_ROOT, path), 'utf8'));

describe('clearLocalWriting', () => {
  it.each([...LOCAL_PREFIXES, ...SESSION_PREFIXES])('"%s" is a key prefix the app still writes', (prefix) => {
    expect(shipped.some((source) => source.includes(prefix))).toBe(true);
  });

  it('removes the writing and leaves the rest', () => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem('chapter-backup-b1-c1', 'x');
    localStorage.setItem('book-summary-unsaved-b1', 'x');
    localStorage.setItem('theme', 'dark');
    sessionStorage.setItem('chapterQuestionsTab_b1_c1', 'questions');
    sessionStorage.setItem('auth:postVerifyRedirect', '/dashboard');

    clearLocalWriting();

    expect(Object.keys(localStorage)).toEqual(['theme']);
    expect(Object.keys(sessionStorage)).toEqual(['auth:postVerifyRedirect']);
  });
});

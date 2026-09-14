import { act } from 'react';
import { renderToString } from 'react-dom/server';
import { hydrateRoot } from 'react-dom/client';
import { ChapterEditor } from '../ChapterEditor';

jest.mock('@/lib/api/bookClient');
jest.mock('../DraftGenerator', () => ({ DraftGenerator: () => <div>Draft Generator</div> }));
jest.mock('../StyleTransformer', () => ({ StyleTransformer: () => <div>Style Transformer</div> }));
jest.mock('../questions/QuestionContainer', () => ({
  __esModule: true,
  default: () => <div data-testid="question-container">Questions</div>,
}));

/**
 * The saved tab view survives hydration without a mismatch (#584).
 *
 * The server cannot read sessionStorage, so it always renders the writing view.
 * A client with a saved "questions" view must still hydrate cleanly and then
 * show that view. The obvious lint fix, a `useState` initializer that reads
 * storage, renders "questions" on the client's first pass and mismatches the
 * server HTML, which is why the restore used to live in an effect.
 */
const props = { bookId: 'book-1', chapterId: 'chapter-1', chapterTitle: 'T', initialContent: '<p>hi</p>' };

it('hydrates cleanly, then shows the view saved on the client', async () => {
  sessionStorage.clear();
  const html = renderToString(<ChapterEditor {...props} />);
  expect(html).not.toContain('question-container');

  sessionStorage.setItem('chapterQuestionsTab_book-1_chapter-1', 'questions');
  const container = document.createElement('div');
  container.innerHTML = html;
  document.body.appendChild(container);

  const recoverable: unknown[] = [];
  const consoleErrors: string[] = [];
  const spy = jest.spyOn(console, 'error').mockImplementation((...args) => {
    consoleErrors.push(args.map(String).join(' '));
  });
  try {
    await act(async () => {
      hydrateRoot(container, <ChapterEditor {...props} />, {
        onRecoverableError: (error) => recoverable.push(error),
      });
    });
  } finally {
    spy.mockRestore();
  }

  expect(recoverable).toEqual([]);
  expect(consoleErrors.filter((e) => /hydrat|did not match|mismatch/i.test(e))).toEqual([]);
  expect(container.querySelector('[data-testid="question-container"]')).not.toBeNull();
});

/** @jest-environment node */
import nextConfig from '../../next.config';

describe('next.config redirects (#1094)', () => {
  it('sends the legacy chapter URL to the book page with the chapter in ?chapter=', async () => {
    const rules = await nextConfig.redirects!();
    expect(rules).toContainEqual({
      source: '/dashboard/books/:bookId/chapters/:chapterId',
      destination: '/dashboard/books/:bookId?chapter=:chapterId',
      permanent: false,
    });
  });
});

'use client';

import dynamic from 'next/dynamic';

/**
 * Code-split boundary for the chapter editor (#347).
 *
 * TipTap/ProseMirror is large; statically imported, it sat in the initial
 * bundle even for a visitor who never opened a chapter.
 *
 * `ssr: false` because the editor is browser-only regardless: ChapterEditor
 * already passes `immediatelyRender: false` to `useEditor` to avoid hydration
 * mismatches.
 */
export const LazyChapterEditor = dynamic(
  () => import('./ChapterEditor').then((m) => m.ChapterEditor),
  {
    ssr: false,
    loading: () => (
      <div
        className="flex-1 flex items-center justify-center p-8"
        role="status"
        aria-live="polite"
      >
        <span className="text-muted-foreground">Loading editor…</span>
      </div>
    ),
  }
);

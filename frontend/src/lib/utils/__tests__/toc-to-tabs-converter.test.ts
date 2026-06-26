/**
 * Tests for toc-to-tabs-converter utility
 *
 * Coverage targets:
 * - convertTocToChapterTabs: null input, empty chapters, flat TOC, nested/subchapters,
 *   field defaults, has_content from content_id, ordering, all status values
 * - hasParentChapter: null/missing data, top-level, sub-level, not found
 * - getParentChapterId: null/missing data, top-level, sub-level, not found
 */

import { convertTocToChapterTabs, hasParentChapter, getParentChapterId } from '../toc-to-tabs-converter';
import { ChapterStatus } from '@/types/chapter-tabs';

// ─── helpers ──────────────────────────────────────────────────────────────────

type SubchapterInput = {
  id: string;
  title?: string;
  level?: number;
  order?: number;
};

type ChapterInput = {
  id: string;
  title?: string;
  level?: number;
  order?: number;
  status?: ChapterStatus;
  word_count?: number;
  last_modified?: string;
  estimated_reading_time?: number;
  content_id?: string;
  subchapters?: SubchapterInput[];
};

function makeChapter(input: ChapterInput) {
  return {
    id: input.id,
    title: input.title ?? `Chapter ${input.id}`,
    level: input.level ?? 1,
    order: input.order ?? 1,
    status: input.status,
    word_count: input.word_count,
    last_modified: input.last_modified,
    estimated_reading_time: input.estimated_reading_time,
    content_id: input.content_id,
    subchapters: (input.subchapters ?? []).map((sub, i) => ({
      id: sub.id,
      title: sub.title ?? `Sub ${sub.id}`,
      level: sub.level ?? 2,
      order: sub.order ?? i + 1,
    })),
  };
}

function makeToc(chapters: ChapterInput[]) {
  return { chapters: chapters.map(makeChapter) };
}

// ─── convertTocToChapterTabs ──────────────────────────────────────────────────

describe('convertTocToChapterTabs', () => {
  describe('null / missing input', () => {
    it('returns [] for null input', () => {
      expect(convertTocToChapterTabs(null)).toEqual([]);
    });

    it('returns [] when chapters property is missing', () => {
      // @ts-expect-error testing bad input
      expect(convertTocToChapterTabs({})).toEqual([]);
    });

    it('returns [] when chapters is null', () => {
      // @ts-expect-error testing bad input
      expect(convertTocToChapterTabs({ chapters: null })).toEqual([]);
    });
  });

  describe('empty chapters list', () => {
    it('returns [] for an empty chapters array', () => {
      expect(convertTocToChapterTabs(makeToc([]))).toEqual([]);
    });
  });

  describe('flat TOC (no subchapters)', () => {
    it('returns one tab per chapter', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1 },
        { id: 'ch-2', order: 2 },
        { id: 'ch-3', order: 3 },
      ]));
      expect(result).toHaveLength(3);
    });

    it('maps id and title correctly', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', title: 'Introduction', order: 1 },
      ]));
      expect(result[0].id).toBe('ch-1');
      expect(result[0].title).toBe('Introduction');
    });

    it('preserves order value', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 5 },
      ]));
      expect(result[0].order).toBe(5);
    });

    it('preserves level value', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', level: 2, order: 1 },
      ]));
      expect(result[0].level).toBe(2);
    });

    it('uses provided status', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, status: ChapterStatus.COMPLETED },
      ]));
      expect(result[0].status).toBe(ChapterStatus.COMPLETED);
    });

    it('defaults to DRAFT when status is missing', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1 },
      ]));
      expect(result[0].status).toBe(ChapterStatus.DRAFT);
    });

    it('uses provided word_count', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, word_count: 1500 },
      ]));
      expect(result[0].word_count).toBe(1500);
    });

    it('defaults word_count to 0 when missing', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1 },
      ]));
      expect(result[0].word_count).toBe(0);
    });

    it('uses provided estimated_reading_time', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, estimated_reading_time: 8 },
      ]));
      expect(result[0].estimated_reading_time).toBe(8);
    });

    it('defaults estimated_reading_time to 0 when missing', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1 },
      ]));
      expect(result[0].estimated_reading_time).toBe(0);
    });

    it('uses provided last_modified', () => {
      const ts = '2024-01-15T10:30:00.000Z';
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, last_modified: ts },
      ]));
      expect(result[0].last_modified).toBe(ts);
    });

    it('defaults last_modified to a valid ISO string when missing', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1 },
      ]));
      expect(result[0].last_modified).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    });

    it('sets has_content to true when content_id is present', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, content_id: 'content-abc' },
      ]));
      expect(result[0].has_content).toBe(true);
    });

    it('sets has_content to false when content_id is absent', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1 },
      ]));
      expect(result[0].has_content).toBe(false);
    });

    it('chapters appear in input order (no reordering by the converter)', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-3', order: 3 },
        { id: 'ch-1', order: 1 },
        { id: 'ch-2', order: 2 },
      ]));
      expect(result.map(t => t.id)).toEqual(['ch-3', 'ch-1', 'ch-2']);
    });
  });

  describe('TOC with subchapters', () => {
    it('parent chapter is followed immediately by its subchapters', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, subchapters: [{ id: 'sub-1' }, { id: 'sub-2' }] },
        { id: 'ch-2', order: 2 },
      ]));
      expect(result.map(t => t.id)).toEqual(['ch-1', 'sub-1', 'sub-2', 'ch-2']);
    });

    it('total count includes parent and subchapters', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, subchapters: [{ id: 'sub-1' }, { id: 'sub-2' }] },
        { id: 'ch-2', order: 2, subchapters: [{ id: 'sub-3' }] },
      ]));
      expect(result).toHaveLength(5); // 2 parents + 3 subs
    });

    it('subchapter id and title are preserved', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, subchapters: [{ id: 'sub-A', title: 'Sub Title A' }] },
      ]));
      const sub = result.find(t => t.id === 'sub-A')!;
      expect(sub.id).toBe('sub-A');
      expect(sub.title).toBe('Sub Title A');
    });

    it('subchapters always get DRAFT status', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, subchapters: [{ id: 'sub-1' }] },
      ]));
      const sub = result.find(t => t.id === 'sub-1')!;
      expect(sub.status).toBe(ChapterStatus.DRAFT);
    });

    it('subchapters always get word_count of 0', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, subchapters: [{ id: 'sub-1' }] },
      ]));
      const sub = result.find(t => t.id === 'sub-1')!;
      expect(sub.word_count).toBe(0);
    });

    it('subchapters always have has_content=false', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, subchapters: [{ id: 'sub-1' }] },
      ]));
      const sub = result.find(t => t.id === 'sub-1')!;
      expect(sub.has_content).toBe(false);
    });

    it('subchapters always have estimated_reading_time of 0', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, subchapters: [{ id: 'sub-1' }] },
      ]));
      const sub = result.find(t => t.id === 'sub-1')!;
      expect(sub.estimated_reading_time).toBe(0);
    });

    it('subchapters preserve their order value', () => {
      const result = convertTocToChapterTabs(makeToc([
        {
          id: 'ch-1', order: 1,
          subchapters: [
            { id: 'sub-1', order: 10 },
            { id: 'sub-2', order: 20 },
          ],
        },
      ]));
      expect(result.find(t => t.id === 'sub-1')!.order).toBe(10);
      expect(result.find(t => t.id === 'sub-2')!.order).toBe(20);
    });

    it('subchapters preserve their level value', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, subchapters: [{ id: 'sub-1', level: 2 }] },
      ]));
      expect(result.find(t => t.id === 'sub-1')!.level).toBe(2);
    });

    it('subchapters have a valid ISO last_modified string', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, subchapters: [{ id: 'sub-1' }] },
      ]));
      const sub = result.find(t => t.id === 'sub-1')!;
      expect(sub.last_modified).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    });

    it('chapter with no subchapters is not followed by any', () => {
      const result = convertTocToChapterTabs(makeToc([
        { id: 'ch-1', order: 1, subchapters: [] },
        { id: 'ch-2', order: 2 },
      ]));
      expect(result.map(t => t.id)).toEqual(['ch-1', 'ch-2']);
    });
  });

  describe('all ChapterStatus values', () => {
    Object.values(ChapterStatus).forEach((status) => {
      it(`preserves status=${status} for main chapters`, () => {
        const result = convertTocToChapterTabs(makeToc([
          { id: 'ch-1', order: 1, status },
        ]));
        expect(result[0].status).toBe(status);
      });
    });
  });
});

// ─── hasParentChapter ─────────────────────────────────────────────────────────

describe('hasParentChapter', () => {
  const toc = makeToc([
    { id: 'ch-1', order: 1, subchapters: [{ id: 'sub-1' }, { id: 'sub-2' }] },
    { id: 'ch-2', order: 2 },
  ]);

  it('returns false for null tocData', () => {
    expect(hasParentChapter('sub-1', null)).toBe(false);
  });

  it('returns false when tocData has no chapters', () => {
    // @ts-expect-error testing bad input
    expect(hasParentChapter('sub-1', {})).toBe(false);
  });

  it('returns false when chapters is null', () => {
    // @ts-expect-error testing bad input
    expect(hasParentChapter('sub-1', { chapters: null })).toBe(false);
  });

  it('returns false for a top-level chapter id', () => {
    expect(hasParentChapter('ch-1', toc)).toBe(false);
  });

  it('returns false for another top-level chapter id', () => {
    expect(hasParentChapter('ch-2', toc)).toBe(false);
  });

  it('returns true for a subchapter id that belongs to a parent', () => {
    expect(hasParentChapter('sub-1', toc)).toBe(true);
  });

  it('returns true for the second subchapter', () => {
    expect(hasParentChapter('sub-2', toc)).toBe(true);
  });

  it('returns false for an id that does not exist in the TOC', () => {
    expect(hasParentChapter('does-not-exist', toc)).toBe(false);
  });

  it('returns false for an empty string id', () => {
    expect(hasParentChapter('', toc)).toBe(false);
  });

  it('works when no chapter has subchapters', () => {
    const flatToc = makeToc([{ id: 'ch-1', order: 1 }, { id: 'ch-2', order: 2 }]);
    expect(hasParentChapter('ch-1', flatToc)).toBe(false);
  });
});

// ─── getParentChapterId ───────────────────────────────────────────────────────

describe('getParentChapterId', () => {
  const toc = makeToc([
    { id: 'ch-1', order: 1, subchapters: [{ id: 'sub-1' }, { id: 'sub-2' }] },
    { id: 'ch-2', order: 2, subchapters: [{ id: 'sub-3' }] },
    { id: 'ch-3', order: 3 },
  ]);

  it('returns null for null tocData', () => {
    expect(getParentChapterId('sub-1', null)).toBeNull();
  });

  it('returns null when tocData has no chapters', () => {
    // @ts-expect-error testing bad input
    expect(getParentChapterId('sub-1', {})).toBeNull();
  });

  it('returns null when chapters is null', () => {
    // @ts-expect-error testing bad input
    expect(getParentChapterId('sub-1', { chapters: null })).toBeNull();
  });

  it('returns null for a top-level chapter id', () => {
    expect(getParentChapterId('ch-1', toc)).toBeNull();
  });

  it('returns null for a top-level chapter that has no parent', () => {
    expect(getParentChapterId('ch-3', toc)).toBeNull();
  });

  it('returns the parent id for sub-1 (child of ch-1)', () => {
    expect(getParentChapterId('sub-1', toc)).toBe('ch-1');
  });

  it('returns the parent id for sub-2 (also child of ch-1)', () => {
    expect(getParentChapterId('sub-2', toc)).toBe('ch-1');
  });

  it('returns the parent id for sub-3 (child of ch-2)', () => {
    expect(getParentChapterId('sub-3', toc)).toBe('ch-2');
  });

  it('returns null for an id that does not exist anywhere', () => {
    expect(getParentChapterId('non-existent', toc)).toBeNull();
  });

  it('returns null for an empty string id', () => {
    expect(getParentChapterId('', toc)).toBeNull();
  });

  it('works when no chapter has subchapters', () => {
    const flatToc = makeToc([{ id: 'ch-1', order: 1 }, { id: 'ch-2', order: 2 }]);
    expect(getParentChapterId('ch-1', flatToc)).toBeNull();
  });
});

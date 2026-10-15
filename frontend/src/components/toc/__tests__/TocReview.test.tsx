/**
 * Tests for TocReview — the "Accept & Continue" loading state added for
 * issue #52, plus TOC structure rendering tests rehomed from
 * src/__tests__/TocGenerationWizard.test.tsx (issue #200).
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import TocReview from '../TocReview';
import { TocGenerationResult } from '@/types/toc';

jest.mock('@/components/ui/ChapterStatusIndicator', () => ({
  ChapterStatusIndicator: () => <span data-testid="status" />,
}));

const tocResult: TocGenerationResult = {
  toc: {
    chapters: [
      { id: 'c1', title: 'Chapter One', description: 'Intro', subchapters: [] },
    ],
    total_chapters: 1,
    estimated_pages: 10,
    structure_notes: '',
  },
  has_subchapters: false,
} as unknown as TocGenerationResult;

function setup(isLoading: boolean) {
  return render(
    <TocReview
      tocResult={tocResult}
      onAccept={jest.fn()}
      onRegenerate={jest.fn()}
      isLoading={isLoading}
    />
  );
}

describe('TocReview Accept button loading state', () => {
  it('shows "Accept & Continue" and is enabled when not loading', () => {
    setup(false);
    const accept = screen.getByRole('button', { name: /accept & continue/i });
    expect(accept).toBeInTheDocument();
    expect(accept).not.toBeDisabled();
  });

  it('shows "Saving..." and disables both buttons when loading', () => {
    setup(true);
    expect(screen.getByText('Saving...')).toBeInTheDocument();
    expect(screen.queryByText(/accept & continue/i)).not.toBeInTheDocument();
    // Regenerate also reflects loading
    expect(screen.getByText('Regenerating...')).toBeInTheDocument();
    // Both action buttons are disabled while saving
    expect(screen.getByText('Saving...').closest('button')).toBeDisabled();
    expect(screen.getByText('Regenerating...').closest('button')).toBeDisabled();
  });
});

describe('TocReview replace warning (#753)', () => {
  const render_ = (replaces_drafts?: number) =>
    render(
      <TocReview
        tocResult={{ ...tocResult, replaces_drafts }}
        onAccept={jest.fn()}
        onRegenerate={jest.fn()}
        isLoading={false}
      />
    );

  it('explains that accepting replaces existing chapter drafts', () => {
    render_(3);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent(/replaces your current table of contents/i);
    expect(alert).toHaveTextContent(/3 chapters with written content/i);
  });

  it('uses the singular for one draft', () => {
    render_(1);
    expect(screen.getByRole('alert')).toHaveTextContent(/1 chapter with written content/i);
  });

  it.each([0, undefined])('shows no warning when nothing would be lost (%s)', (n) => {
    render_(n);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('TocReview structure rendering', () => {
  function renderToc(chapters: unknown[]) {
    const result = {
      toc: {
        chapters,
        total_chapters: chapters.length,
        estimated_pages: 10,
        structure_notes: 'Test structure notes.',
      },
      success: true,
      chapters_count: chapters.length,
      has_subchapters: true,
    } as unknown as TocGenerationResult;
    return render(
      <TocReview
        tocResult={result}
        onAccept={jest.fn()}
        onRegenerate={jest.fn()}
        isLoading={false}
      />
    );
  }

  it('displays top-level chapters and reveals subchapters on expand', () => {
    renderToc([
      {
        id: 'ch1',
        title: 'Chapter 1',
        description: '',
        level: 1,
        order: 1,
        subchapters: [
          { id: 'ch1-1', title: 'Section 1.1', description: '', level: 2, order: 1 },
        ],
      },
      { id: 'ch2', title: 'Chapter 2', description: '', level: 1, order: 2, subchapters: [] },
    ]);

    expect(screen.getByText(/Chapter 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Chapter 2/i)).toBeInTheDocument();
    // Subchapters are collapsed by default
    expect(screen.queryByText(/Section 1\.1/i)).not.toBeInTheDocument();

    const chapter1 = screen.getByText(/Chapter 1/i).closest('.cursor-pointer');
    expect(chapter1).not.toBeNull();
    fireEvent.click(chapter1!);
    expect(screen.getByText(/Section 1\.1/i)).toBeInTheDocument();
  });

  it('renders deeply nested subchapters and empty chapters', () => {
    renderToc([
      {
        id: 'ch1',
        title: 'Intro',
        description: '',
        level: 1,
        order: 1,
        subchapters: [
          {
            id: 'ch1-1',
            title: 'Background',
            description: '',
            level: 2,
            order: 1,
            subchapters: [
              { id: 'ch1-1-1', title: 'History', description: '', level: 3, order: 1 },
            ],
          },
          { id: 'ch1-2', title: 'Scope', description: '', level: 2, order: 2, subchapters: [] },
        ],
      },
      { id: 'ch2', title: 'Empty Chapter', description: '', level: 1, order: 2, subchapters: [] },
    ]);

    expect(screen.getByText(/Intro/i)).toBeInTheDocument();
    expect(screen.getByText(/Empty Chapter/i)).toBeInTheDocument();

    const intro = screen.getByText(/Intro/i).closest('.cursor-pointer');
    expect(intro).not.toBeNull();
    fireEvent.click(intro!);
    expect(screen.getByText(/Background/i)).toBeInTheDocument();
    expect(screen.getByText(/Scope/i)).toBeInTheDocument();

    const background = screen.getByText(/Background/i).closest('.cursor-pointer');
    expect(background).not.toBeNull();
    fireEvent.click(background!);
    expect(screen.getByText(/History/i)).toBeInTheDocument();
  });
});

describe('TocReview counts that are zero (#855)', () => {
  const withChapters = (chapters: object[]) =>
    render(
      <TocReview
        tocResult={{ ...tocResult, toc: { ...tocResult.toc, chapters } } as unknown as TocGenerationResult}
        onAccept={jest.fn()}
        onRegenerate={jest.fn()}
        isLoading={false}
      />
    );

  it('renders no stray "0" for a chapter with no words or no reading time', () => {
    const { container } = withChapters([
      { id: 'c1', title: 'Empty', description: '', subchapters: [], word_count: 0, estimated_reading_time: 0 },
      { id: 'c2', title: 'Short', description: '', subchapters: [], word_count: 120, estimated_reading_time: 0 },
    ]);

    expect(screen.getByText('120 words')).toBeInTheDocument();
    const text = container.textContent ?? '';
    expect(text).not.toMatch(/Empty0|0min|words0/);
  });
});

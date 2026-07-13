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

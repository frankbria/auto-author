/**
 * Tests for TocReview — focused on the "Accept & Continue" loading state
 * added for issue #52 (comprehensive loading indicators).
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
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

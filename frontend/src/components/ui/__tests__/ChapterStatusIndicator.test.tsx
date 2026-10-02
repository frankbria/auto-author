import { render, screen } from '@testing-library/react';
import { ChapterStatusIndicator } from '../ChapterStatusIndicator';
import { ChapterStatus } from '@/types/chapter-tabs';
import { ChapterStatus as BookChapterStatus } from '@/types/book';

describe('ChapterStatusIndicator (#861)', () => {
  it('has one ChapterStatus enum, whose in-progress value is the backend value', () => {
    expect(ChapterStatus).toBe(BookChapterStatus);
    expect(ChapterStatus.IN_PROGRESS).toBe('in-progress');
  });

  it("renders 'In Progress' for the backend's 'in-progress' value", () => {
    render(<ChapterStatusIndicator status={'in-progress' as ChapterStatus} showLabel showIcon />);
    expect(screen.getByText('In Progress')).toBeInTheDocument();
  });

  it.each<[{ showLabel?: boolean; showIcon?: boolean }]>([
    [{ showLabel: true }],
    [{ showIcon: true }],
    [{ showLabel: true, showIcon: true }],
    [{}],
  ])('falls back to the draft config for an unknown status instead of throwing (%j)', (props) => {
    const { container } = render(
      <ChapterStatusIndicator status={'bogus' as ChapterStatus} {...props} />
    );
    expect(container.firstChild).not.toBeNull();
    if (props.showLabel) expect(screen.getByText('Draft')).toBeInTheDocument();
  });
});

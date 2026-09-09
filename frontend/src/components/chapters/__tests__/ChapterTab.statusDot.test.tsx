import { render, screen } from '@testing-library/react';
import { TooltipProvider } from '@/components/ui/tooltip';
import { ChapterTab } from '../ChapterTab';
import { ChapterStatus } from '@/types/chapter-tabs';

/**
 * Guard for the status dot found during #618: every `statusConfig` colour is
 * merged onto the dot AFTER a base class list, so `twMerge` keeps the config
 * colour and drops anything in the base — the old `bg-white` fallback never
 * rendered. `DRAFT` was `bg-muted`, which is also the inactive tab's own
 * surface, so the default-state dot was invisible against its own tab.
 */
const chapter = {
  id: 'ch1',
  title: 'Draft chapter',
  status: ChapterStatus.DRAFT,
  word_count: 0,
  estimated_reading_time: 0,
  has_unsaved_changes: false,
  is_loading: false,
} as never;

it('the draft status dot does not use the inactive tab surface as its fill (#618)', () => {
  render(
    <TooltipProvider>
      <ChapterTab chapter={chapter} isActive={false} onSelect={jest.fn()} onClose={jest.fn()} />
    </TooltipProvider>
  );

  const tab = screen.getByTestId('chapter-tab');
  const dot = tab.querySelector('.rounded-full');
  const surface = [...tab.classList].filter((c) => c.startsWith('bg-'));
  const fill = [...(dot?.classList ?? [])].filter((c) => c.startsWith('bg-'));

  expect(surface).toContain('bg-muted');
  expect(fill).not.toHaveLength(0);
  expect(surface).not.toEqual(expect.arrayContaining(fill));
});

/** A list of every chapter, to reopen a closed tab from (#1043). */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TabBar } from '../TabBar';
import { ChapterStatus } from '@/types/chapter-tabs';

const chapter = (id: string) => ({
  id, title: `Title ${id}`, status: ChapterStatus.DRAFT, word_count: 0, last_modified: '', estimated_reading_time: 0,
  order: 1, level: 1, has_content: false,
});

function setup(onTabSelect = jest.fn()) {
  render(
    <TabBar
      chapters={[chapter('c1'), chapter('c2'), chapter('c3')]}
      activeChapterId="c1"
      tabOrder={['c1', 'c3']}
      onTabSelect={onTabSelect}
      onTabReorder={jest.fn()}
      onTabClose={jest.fn()}
    />,
  );
  return onTabSelect;
}

describe('TabBar all-chapters list', () => {
  it('lists every chapter, marks the closed one, and reopens it', async () => {
    const onTabSelect = setup();
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: 'All chapters' }));

    expect(screen.getAllByRole('menuitem')).toHaveLength(3);
    await user.click(screen.getByRole('menuitem', { name: /Title c2.*closed/i }));
    expect(onTabSelect).toHaveBeenCalledWith('c2');
  });

  it('opens from the keyboard', async () => {
    const onTabSelect = setup();
    const user = userEvent.setup();

    screen.getByRole('button', { name: 'All chapters' }).focus();
    await user.keyboard('{Enter}');
    await user.keyboard('{ArrowDown}{ArrowDown}{Enter}');

    expect(onTabSelect).toHaveBeenCalled();
  });
});

/**
 * Saved tab state, made to agree with the chapters the book has now (#830).
 *
 * Tab state is saved and restored, and the table of contents changes in
 * between: a chapter is added, another deleted. Used when the tabs load and
 * each time they refresh, so both end up in the same place.
 *
 * - Chapters that are gone are dropped from the open tabs and from the order.
 * - Chapters not in the saved order get a tab after the ones that are, except
 *   the ones the writer closed (`closed_tab_ids`, #1043): those stay hidden
 *   until reopened, so a chapter added later still gets a tab and a closed one
 *   does not. A state saved without the field closes nothing.
 * - The active chapter is the one asked for (a `?chapter=` link) if the book
 *   has it, else the saved one if the book still has it, else the first open
 *   tab, else the first chapter. It is always one of the open tabs.
 */
export interface SavedTabState {
  active_chapter_id?: string | null;
  open_tab_ids?: string[];
  tab_order?: string[];
  closed_tab_ids?: string[];
}

export function reconcileTabState(
  chapterIds: string[],
  saved: SavedTabState,
  preferred?: string | null,
): { active_chapter_id: string | null; open_tab_ids: string[]; tab_order: string[]; closed_tab_ids: string[] } {
  const exists = new Set(chapterIds);
  const stillThere = (ids: string[] | undefined) => [...new Set(ids ?? [])].filter(id => exists.has(id));

  const open = stillThere(saved.open_tab_ids);
  const active =
    [preferred, saved.active_chapter_id, open[0], chapterIds[0]].find(id => id != null && exists.has(id)) ?? null;
  // The active chapter is on screen, so it is not closed.
  const closed = stillThere(saved.closed_tab_ids).filter(id => id !== active);
  const order = stillThere(saved.tab_order).filter(id => !closed.includes(id));

  return {
    active_chapter_id: active,
    open_tab_ids: (active && !open.includes(active) ? [...open, active] : open).filter(id => !closed.includes(id)),
    tab_order: [...order, ...chapterIds.filter(id => !order.includes(id) && !closed.includes(id))],
    closed_tab_ids: closed,
  };
}

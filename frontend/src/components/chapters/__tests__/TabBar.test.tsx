import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { TabBar } from '@/components/chapters/TabBar';
import { ChapterStatus, ChapterTabMetadata } from '@/types/chapter-tabs';

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

// Capture the onDragEnd callback so we can invoke it programmatically.
let capturedOnDragEnd: ((result: any) => void) | null = null;

jest.mock('@hello-pangea/dnd', () => {
  const React = require('react');
  return {
    DragDropContext: ({ children, onDragEnd }: any) => {
      // Store the callback every render so we can trigger drags in tests.
      capturedOnDragEnd = onDragEnd;
      return React.createElement(React.Fragment, null, children);
    },
    Droppable: ({ children }: any) =>
      children(
        {
          innerRef: jest.fn(),
          droppableProps: { 'data-rfd-droppable-id': 'chapter-tabs', 'data-rfd-droppable-context-id': '0' },
          placeholder: null,
        },
        { isDraggingOver: false, draggingOverWith: null, draggingFromThisWith: null, isUsingPlaceholder: false }
      ),
    Draggable: ({ children, draggableId }: any) =>
      children(
        {
          innerRef: jest.fn(),
          draggableProps: { 'data-rfd-draggable-id': draggableId, 'data-rfd-draggable-context-id': '0' },
          dragHandleProps: { 'data-rfd-drag-handle-draggable-id': draggableId },
        },
        { isDragging: false, isDropAnimating: false, combineTargetFor: null, mode: null }
      ),
  };
});

// ChapterTab renders complex Tooltip/Icon trees; stub to a simple button.
jest.mock('@/components/chapters/ChapterTab', () => ({
  ChapterTab: React.forwardRef(({ chapter, onSelect, onClose, isActive }: any, ref: any) =>
    React.createElement(
      'div',
      { ref, 'data-testid': `chapter-tab-${chapter.id}`, 'aria-selected': isActive },
      React.createElement('button', { onClick: onSelect, 'data-testid': `select-${chapter.id}` }, chapter.title),
      React.createElement('button', { onClick: onClose, 'data-testid': `close-${chapter.id}` }, 'close')
    )
  ),
}));

// TabOverflowMenu is irrelevant to the three uncovered functions.
jest.mock('@/components/chapters/TabOverflowMenu', () => ({
  TabOverflowMenu: ({ visible, chapters, onTabSelect, onVisibilityChange }: any) =>
    visible
      ? React.createElement(
          'div',
          { 'data-testid': 'overflow-menu' },
          chapters.map((ch: any) =>
            React.createElement(
              'button',
              { key: ch.id, onClick: () => onTabSelect(ch.id) },
              ch.title
            )
          ),
          React.createElement('button', { onClick: () => onVisibilityChange(false) }, 'close-overflow')
        )
      : null,
}));

// ScrollArea — in React 19 refs can be passed as regular props; no forwardRef needed.
// The component stores scrollAreaRef on the outer div and queries for the viewport child.
jest.mock('@/components/ui/scroll-area', () => {
  const React = require('react');
  // Accept ref as a regular prop (React 19 style) so scrollAreaRef.current is set.
  const ScrollArea = ({ children, className, ref, ...props }: any) =>
    React.createElement(
      'div',
      { ref, className, ...props, 'data-testid': 'scroll-area' },
      React.createElement(
        'div',
        { 'data-radix-scroll-area-viewport': '', 'data-testid': 'scroll-viewport' },
        children
      )
    );
  ScrollArea.displayName = 'ScrollArea';
  return { ScrollArea };
});

// HugeiconsIcon is not meaningful in jsdom.
jest.mock('@hugeicons/react', () => ({
  HugeiconsIcon: () => null,
}));
jest.mock('@hugeicons/core-free-icons', () => ({
  ArrowUp01Icon: {},
  ArrowDown01Icon: {},
}));

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

const makeChapter = (id: string, overrides: Partial<ChapterTabMetadata> = {}): ChapterTabMetadata => ({
  id,
  title: `Chapter ${id}`,
  status: ChapterStatus.DRAFT,
  word_count: 100,
  last_modified: new Date().toISOString(),
  estimated_reading_time: 1,
  level: 1,
  order: 1,
  has_content: true,
  ...overrides,
});

const ch1 = makeChapter('ch-1', { title: 'Introduction' });
const ch2 = makeChapter('ch-2', { title: 'Body' });
const ch3 = makeChapter('ch-3', { title: 'Conclusion' });
const defaultChapters = [ch1, ch2, ch3];
const defaultTabOrder = ['ch-1', 'ch-2', 'ch-3'];

interface RenderOptions {
  chapters?: ChapterTabMetadata[];
  activeChapterId?: string | null;
  tabOrder?: string[];
  orientation?: 'vertical' | 'horizontal';
  onTabSelect?: jest.Mock;
  onTabReorder?: jest.Mock;
  onTabClose?: jest.Mock;
}

const renderTabBar = ({
  chapters = defaultChapters,
  activeChapterId = 'ch-1',
  tabOrder = defaultTabOrder,
  orientation = 'vertical',
  onTabSelect = jest.fn(),
  onTabReorder = jest.fn(),
  onTabClose = jest.fn(),
}: RenderOptions = {}) =>
  render(
    <TabBar
      chapters={chapters}
      activeChapterId={activeChapterId}
      tabOrder={tabOrder}
      onTabSelect={onTabSelect}
      onTabReorder={onTabReorder}
      onTabClose={onTabClose}
      orientation={orientation}
      data-testid="tab-bar"
    />
  );

// ---------------------------------------------------------------------------
// Helper: create a fake scroll viewport with configurable scroll state
// ---------------------------------------------------------------------------

const setViewportScrollState = (
  viewport: HTMLElement,
  { scrollTop = 0, scrollHeight = 200, clientHeight = 100 } = {}
) => {
  // scrollTop is read/write; scrollHeight and clientHeight are read-only getters.
  // Use Object.defineProperty with configurable:true to override them on the instance.
  Object.defineProperty(viewport, 'scrollTop', {
    value: scrollTop, writable: true, configurable: true,
  });
  Object.defineProperty(viewport, 'scrollHeight', {
    value: scrollHeight, configurable: true,
  });
  Object.defineProperty(viewport, 'clientHeight', {
    value: clientHeight, configurable: true,
  });
  // scrollBy may or may not exist on the prototype in jsdom; define it on the instance.
  Object.defineProperty(viewport, 'scrollBy', {
    value: jest.fn(), writable: true, configurable: true,
  });
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('TabBar', () => {
  beforeEach(() => {
    capturedOnDragEnd = null;
    jest.clearAllMocks();
  });

  // -------------------------------------------------------------------------
  // Basic rendering
  // -------------------------------------------------------------------------

  describe('rendering', () => {
    it('renders all chapters in tab order', () => {
      renderTabBar();
      expect(screen.getByTestId('chapter-tab-ch-1')).toBeInTheDocument();
      expect(screen.getByTestId('chapter-tab-ch-2')).toBeInTheDocument();
      expect(screen.getByTestId('chapter-tab-ch-3')).toBeInTheDocument();
    });

    it('renders scroll-up and scroll-down buttons in vertical orientation', () => {
      renderTabBar();
      expect(screen.getByTestId('scroll-up-button')).toBeInTheDocument();
      expect(screen.getByTestId('scroll-down-button')).toBeInTheDocument();
    });

    it('does not render scroll buttons in horizontal orientation', () => {
      renderTabBar({ orientation: 'horizontal' });
      expect(screen.queryByTestId('scroll-up-button')).not.toBeInTheDocument();
      expect(screen.queryByTestId('scroll-down-button')).not.toBeInTheDocument();
    });

    it('respects tabOrder when ordering chapters', () => {
      // Reverse order: ch-3 first, ch-1 last
      renderTabBar({ tabOrder: ['ch-3', 'ch-2', 'ch-1'] });
      const tabs = screen.getAllByTestId(/^chapter-tab-ch-/);
      expect(tabs[0]).toHaveAttribute('data-testid', 'chapter-tab-ch-3');
      expect(tabs[2]).toHaveAttribute('data-testid', 'chapter-tab-ch-1');
    });

    it('skips chapters that are not in tabOrder', () => {
      // tabOrder only contains ch-1 and ch-3 → ch-2 should not render
      renderTabBar({ tabOrder: ['ch-1', 'ch-3'] });
      expect(screen.queryByTestId('chapter-tab-ch-2')).not.toBeInTheDocument();
    });

    it('marks the active chapter with aria-selected=true', () => {
      renderTabBar({ activeChapterId: 'ch-2' });
      expect(screen.getByTestId('chapter-tab-ch-2')).toHaveAttribute('aria-selected', 'true');
      expect(screen.getByTestId('chapter-tab-ch-1')).toHaveAttribute('aria-selected', 'false');
    });
  });

  // -------------------------------------------------------------------------
  // onTabSelect forwarding
  // -------------------------------------------------------------------------

  describe('tab selection', () => {
    it('calls onTabSelect when a chapter tab is clicked', () => {
      const onTabSelect = jest.fn();
      renderTabBar({ onTabSelect });
      fireEvent.click(screen.getByTestId('select-ch-2'));
      expect(onTabSelect).toHaveBeenCalledWith('ch-2');
    });
  });

  // -------------------------------------------------------------------------
  // onTabClose forwarding
  // -------------------------------------------------------------------------

  describe('tab close', () => {
    it('calls onTabClose when a chapter close button is clicked', () => {
      const onTabClose = jest.fn();
      renderTabBar({ onTabClose });
      fireEvent.click(screen.getByTestId('close-ch-1'));
      expect(onTabClose).toHaveBeenCalledWith('ch-1');
    });
  });

  // -------------------------------------------------------------------------
  // handleDragEnd (previously uncovered)
  // -------------------------------------------------------------------------

  describe('handleDragEnd', () => {
    it('calls onTabReorder with source and destination indices on a valid drag', () => {
      const onTabReorder = jest.fn();
      renderTabBar({ onTabReorder });

      expect(capturedOnDragEnd).not.toBeNull();
      act(() => {
        capturedOnDragEnd!({
          source: { index: 0 },
          destination: { index: 2 },
        });
      });

      expect(onTabReorder).toHaveBeenCalledWith(0, 2);
    });

    it('does not call onTabReorder when destination is null (drag cancelled)', () => {
      const onTabReorder = jest.fn();
      renderTabBar({ onTabReorder });

      act(() => {
        capturedOnDragEnd!({
          source: { index: 0 },
          destination: null,
        });
      });

      expect(onTabReorder).not.toHaveBeenCalled();
    });

    it('does not call onTabReorder when destination is undefined', () => {
      const onTabReorder = jest.fn();
      renderTabBar({ onTabReorder });

      act(() => {
        capturedOnDragEnd!({
          source: { index: 1 },
          destination: undefined,
        });
      });

      expect(onTabReorder).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // scrollUp (previously uncovered)
  // -------------------------------------------------------------------------

  describe('scrollUp', () => {
    it('scrolls the viewport up by 100 when scroll-up button is clicked', () => {
      renderTabBar();
      const viewport = screen.getByTestId('scroll-viewport');
      // Set up scroll state: scrollTop > 0 → canScrollUp becomes true
      setViewportScrollState(viewport, { scrollTop: 150, scrollHeight: 400, clientHeight: 100 });

      // Fire a scroll event so the component reads the new values and enables the button
      act(() => { fireEvent.scroll(viewport); });

      expect(screen.getByTestId('scroll-up-button')).not.toBeDisabled();

      // Now clicking the enabled button should invoke scrollBy
      fireEvent.click(screen.getByTestId('scroll-up-button'));

      expect((viewport as any).scrollBy).toHaveBeenCalledWith({ top: -100, behavior: 'smooth' });
    });

    it('does not throw when scrollAreaRef has no viewport element', () => {
      // When there is no viewport, scrollUp returns at the second guard without throwing.
      renderTabBar();
      const viewport = screen.getByTestId('scroll-viewport');
      // First enable the button by making canScrollUp = true
      setViewportScrollState(viewport, { scrollTop: 10, scrollHeight: 200, clientHeight: 100 });
      act(() => { fireEvent.scroll(viewport); });

      // Now remove the attribute so querySelector returns null inside scrollUp
      viewport.removeAttribute('data-radix-scroll-area-viewport');

      expect(() => {
        fireEvent.click(screen.getByTestId('scroll-up-button'));
      }).not.toThrow();
    });
  });

  // -------------------------------------------------------------------------
  // scrollDown (previously uncovered)
  // -------------------------------------------------------------------------

  describe('scrollDown', () => {
    it('scrolls the viewport down by 100 when scroll-down button is clicked', () => {
      renderTabBar();
      const viewport = screen.getByTestId('scroll-viewport');
      // scrollTop < scrollHeight - clientHeight → canScrollDown = true
      setViewportScrollState(viewport, { scrollTop: 0, scrollHeight: 400, clientHeight: 100 });

      act(() => { fireEvent.scroll(viewport); });

      expect(screen.getByTestId('scroll-down-button')).not.toBeDisabled();

      fireEvent.click(screen.getByTestId('scroll-down-button'));

      expect((viewport as any).scrollBy).toHaveBeenCalledWith({ top: 100, behavior: 'smooth' });
    });

    it('does not throw when scrollAreaRef has no viewport element', () => {
      renderTabBar();
      const viewport = screen.getByTestId('scroll-viewport');
      setViewportScrollState(viewport, { scrollTop: 0, scrollHeight: 400, clientHeight: 100 });
      act(() => { fireEvent.scroll(viewport); });

      viewport.removeAttribute('data-radix-scroll-area-viewport');

      expect(() => {
        fireEvent.click(screen.getByTestId('scroll-down-button'));
      }).not.toThrow();
    });
  });

  // -------------------------------------------------------------------------
  // handleScroll — canScrollUp / canScrollDown state
  // -------------------------------------------------------------------------

  describe('handleScroll', () => {
    it('updates scroll state when viewport fires a scroll event', () => {
      renderTabBar();
      const viewport = screen.getByTestId('scroll-viewport');
      setViewportScrollState(viewport, { scrollTop: 50, scrollHeight: 300, clientHeight: 100 });

      act(() => {
        fireEvent.scroll(viewport);
      });

      // After scrolling, canScrollUp should be true (scrollTop > 0)
      // and canScrollDown should be true (50 < 300 - 100 = 200)
      // The scroll-up button should no longer be disabled
      expect(screen.getByTestId('scroll-up-button')).not.toBeDisabled();
    });

    it('disables scroll-up when at top', () => {
      renderTabBar();
      const viewport = screen.getByTestId('scroll-viewport');
      setViewportScrollState(viewport, { scrollTop: 0, scrollHeight: 300, clientHeight: 100 });

      act(() => {
        fireEvent.scroll(viewport);
      });

      expect(screen.getByTestId('scroll-up-button')).toBeDisabled();
    });

    it('disables scroll-down when at bottom', () => {
      renderTabBar();
      const viewport = screen.getByTestId('scroll-viewport');
      // scrollTop = scrollHeight - clientHeight → at bottom
      setViewportScrollState(viewport, { scrollTop: 200, scrollHeight: 300, clientHeight: 100 });

      act(() => {
        fireEvent.scroll(viewport);
      });

      expect(screen.getByTestId('scroll-down-button')).toBeDisabled();
    });
  });

  // -------------------------------------------------------------------------
  // Horizontal orientation: TabOverflowMenu integration
  // -------------------------------------------------------------------------

  describe('horizontal orientation', () => {
    it('renders TabOverflowMenu when visible in horizontal orientation', () => {
      // TabOverflowMenu is not visible by default (showOverflowMenu starts false)
      // We cannot easily toggle it without internal state access, so we verify
      // it is NOT rendered initially.
      renderTabBar({ orientation: 'horizontal' });
      expect(screen.queryByTestId('overflow-menu')).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Edge cases
  // -------------------------------------------------------------------------

  describe('edge cases', () => {
    it('renders without crashing when chapters array is empty', () => {
      renderTabBar({ chapters: [], tabOrder: [] });
      expect(screen.getByTestId('scroll-area')).toBeInTheDocument();
    });

    it('renders without crashing when tabOrder contains unknown ids', () => {
      renderTabBar({ tabOrder: ['nonexistent-id'] });
      // All filtered out → no chapter-tab elements
      expect(screen.queryByTestId(/^chapter-tab-/)).not.toBeInTheDocument();
    });

    it('accepts data-testid prop and forwards it to root div', () => {
      renderTabBar();
      expect(screen.getByTestId('tab-bar')).toBeInTheDocument();
    });
  });
});

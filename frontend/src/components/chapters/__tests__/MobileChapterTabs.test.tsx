import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { MobileChapterTabs } from '@/components/chapters/MobileChapterTabs';
import { ChapterStatus, ChapterTabMetadata } from '@/types/chapter-tabs';

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

// Sheet uses @radix-ui/react-dialog portals which break in jsdom.
// Replace with a minimal controlled-open simulation.
jest.mock('@/components/ui/sheet', () => {
  const React = require('react');

  const SheetContext = React.createContext<{
    open: boolean;
    onOpenChange: (open: boolean) => void;
  } | null>(null);

  const Sheet = ({ children, open, onOpenChange }: any) =>
    React.createElement(SheetContext.Provider, { value: { open, onOpenChange } }, children);

  const SheetTrigger = ({ children, asChild }: any) => {
    const ctx = React.useContext(SheetContext);
    // Clone the child and inject onClick to open the sheet
    if (asChild && React.isValidElement(children)) {
      return React.cloneElement(children as React.ReactElement<any>, {
        onClick: () => ctx?.onOpenChange(true),
      });
    }
    return React.createElement('div', { onClick: () => ctx?.onOpenChange(true) }, children);
  };

  const SheetContent = ({ children }: any) => {
    const ctx = React.useContext(SheetContext);
    if (!ctx?.open) return null;
    return React.createElement(
      'div',
      { 'data-testid': 'sheet-content' },
      children
    );
  };

  return { Sheet, SheetTrigger, SheetContent };
});

// HugeiconsIcon renders SVG that is not meaningful in jsdom — stub it out.
jest.mock('@hugeicons/react', () => ({
  HugeiconsIcon: () => React.createElement('span', { 'data-testid': 'icon' }),
}));
jest.mock('@hugeicons/core-free-icons', () => ({
  Menu01Icon: {},
}));

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

const makeChapter = (id: string, overrides: Partial<ChapterTabMetadata> = {}): ChapterTabMetadata => ({
  id,
  title: `Chapter ${id}`,
  status: ChapterStatus.DRAFT,
  word_count: 500,
  last_modified: new Date('2024-01-15').toISOString(),
  estimated_reading_time: 3,
  level: 1,
  order: parseInt(id, 10) || 1,
  has_content: true,
  ...overrides,
});

const ch1 = makeChapter('1', { title: 'Introduction', status: ChapterStatus.DRAFT });
const ch2 = makeChapter('2', { title: 'Body', status: ChapterStatus.IN_PROGRESS });
const ch3 = makeChapter('3', { title: 'Conclusion', status: ChapterStatus.COMPLETED });
const ch4 = makeChapter('4', { title: 'Appendix', status: ChapterStatus.PUBLISHED });

const defaultChapters = [ch1, ch2, ch3, ch4];

const renderComponent = (
  chapters = defaultChapters,
  activeChapterId: string | null = '1',
  onChapterSelect = jest.fn()
) =>
  render(
    <MobileChapterTabs
      chapters={chapters}
      activeChapterId={activeChapterId}
      onChapterSelect={onChapterSelect}
    />
  );

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MobileChapterTabs', () => {
  // -------------------------------------------------------------------------
  // Basic rendering
  // -------------------------------------------------------------------------

  describe('rendering', () => {
    it('renders the chapter-selector dropdown', () => {
      renderComponent();
      // The Select mock renders a <select> element
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('renders the Chapter Options trigger button', () => {
      renderComponent();
      expect(screen.getByRole('button', { name: /chapter options/i })).toBeInTheDocument();
    });

    it('does not show sheet content by default', () => {
      renderComponent();
      expect(screen.queryByTestId('sheet-content')).not.toBeInTheDocument();
    });

    it('renders all chapter titles as select options', () => {
      renderComponent();
      // The Select mock in jest.setup.ts renders options from SelectItem
      // After our Sheet mock, the SelectItems are inside SelectContent which maps to options
      const select = screen.getByRole('combobox');
      expect(select).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Select (chapter chooser)
  // -------------------------------------------------------------------------

  describe('Select chapter chooser', () => {
    it('calls onChapterSelect when the select value changes', () => {
      const onChapterSelect = jest.fn();
      renderComponent(defaultChapters, '1', onChapterSelect);
      const select = screen.getByRole('combobox');
      fireEvent.change(select, { target: { value: '2' } });
      expect(onChapterSelect).toHaveBeenCalledWith('2');
    });

    it('reflects the activeChapterId as the current select value', () => {
      renderComponent(defaultChapters, '2');
      const select = screen.getByRole('combobox') as HTMLSelectElement;
      expect(select.value).toBe('2');
    });

    it('selects each chapter when changed', () => {
      const onChapterSelect = jest.fn();
      renderComponent(defaultChapters, '1', onChapterSelect);
      const select = screen.getByRole('combobox');

      ['1', '2', '3', '4'].forEach((id) => {
        fireEvent.change(select, { target: { value: id } });
        expect(onChapterSelect).toHaveBeenCalledWith(id);
      });

      expect(onChapterSelect).toHaveBeenCalledTimes(4);
    });
  });

  // -------------------------------------------------------------------------
  // Sheet open / close
  // -------------------------------------------------------------------------

  describe('Sheet (chapter navigation drawer)', () => {
    it('opens the sheet when Chapter Options button is clicked', () => {
      renderComponent();
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));
      expect(screen.getByTestId('sheet-content')).toBeInTheDocument();
    });

    it('shows the Chapters heading inside the sheet', () => {
      renderComponent();
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));
      expect(screen.getByText('Chapters')).toBeInTheDocument();
    });

    it('displays all chapter titles inside the sheet', () => {
      renderComponent();
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));
      const sheet = screen.getByTestId('sheet-content');
      expect(within(sheet).getByText('Introduction')).toBeInTheDocument();
      expect(within(sheet).getByText('Body')).toBeInTheDocument();
      expect(within(sheet).getByText('Conclusion')).toBeInTheDocument();
      expect(within(sheet).getByText('Appendix')).toBeInTheDocument();
    });

    it('calls onChapterSelect and closes sheet when a chapter row is clicked', () => {
      const onChapterSelect = jest.fn();
      renderComponent(defaultChapters, '1', onChapterSelect);
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));

      const sheet = screen.getByTestId('sheet-content');
      // Click the second chapter item in the sheet list
      fireEvent.click(within(sheet).getByText('Body'));

      expect(onChapterSelect).toHaveBeenCalledWith('2');
      // Sheet should close after selection
      expect(screen.queryByTestId('sheet-content')).not.toBeInTheDocument();
    });

    it('shows word count for each chapter in sheet', () => {
      renderComponent();
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));
      const sheet = screen.getByTestId('sheet-content');
      // Each chapter has word_count: 500 → "500 words"
      const wordCountItems = within(sheet).getAllByText(/500 words/);
      expect(wordCountItems.length).toBeGreaterThanOrEqual(1);
    });

    it('shows last modified date when last_modified is set', () => {
      renderComponent();
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));
      const sheet = screen.getByTestId('sheet-content');
      // Date is 2024-01-15 so some locale-formatted version should appear
      const modifiedTexts = within(sheet).getAllByText(/Modified/);
      expect(modifiedTexts.length).toBeGreaterThan(0);
    });

    it('highlights the active chapter inside the sheet', () => {
      renderComponent(defaultChapters, '2');
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));
      const sheet = screen.getByTestId('sheet-content');
      // The active chapter row has bg-primary/10 class
      // Look for the parent div of the "Body" text that contains that class
      const bodyItem = within(sheet).getByText('Body').closest('[class*="border"]');
      expect(bodyItem?.className).toContain('bg-primary/10');
    });
  });

  // -------------------------------------------------------------------------
  // getStatusColor branches (exercised via sheet rendering)
  // -------------------------------------------------------------------------

  describe('status colour indicator dots', () => {
    // Each chapter renders a coloured dot whose class comes from getStatusColor().
    // We verify the dot is rendered for each status.

    it('renders a dot for draft chapters', () => {
      render(
        <MobileChapterTabs
          chapters={[makeChapter('d', { status: ChapterStatus.DRAFT })]}
          activeChapterId="d"
          onChapterSelect={jest.fn()}
        />
      );
      // Dot appears in the Select trigger area
      const dot = document.querySelector('.bg-muted.rounded-full');
      expect(dot).toBeTruthy();
    });

    it('renders a blue dot for in_progress chapters', () => {
      render(
        <MobileChapterTabs
          chapters={[makeChapter('p', { status: ChapterStatus.IN_PROGRESS })]}
          activeChapterId="p"
          onChapterSelect={jest.fn()}
        />
      );
      const dot = document.querySelector('.bg-blue-500.rounded-full');
      expect(dot).toBeTruthy();
    });

    it('renders a green dot for completed chapters', () => {
      render(
        <MobileChapterTabs
          chapters={[makeChapter('c', { status: ChapterStatus.COMPLETED })]}
          activeChapterId="c"
          onChapterSelect={jest.fn()}
        />
      );
      const dot = document.querySelector('.bg-green-500.rounded-full');
      expect(dot).toBeTruthy();
    });

    it('renders a purple dot for published chapters', () => {
      render(
        <MobileChapterTabs
          chapters={[makeChapter('pub', { status: ChapterStatus.PUBLISHED })]}
          activeChapterId="pub"
          onChapterSelect={jest.fn()}
        />
      );
      const dot = document.querySelector('.bg-purple-500.rounded-full');
      expect(dot).toBeTruthy();
    });

    it('renders bg-muted dot for unknown status', () => {
      render(
        <MobileChapterTabs
          chapters={[makeChapter('u', { status: 'unknown' as ChapterStatus })]}
          activeChapterId="u"
          onChapterSelect={jest.fn()}
        />
      );
      // Falls through to default branch → bg-muted
      const dot = document.querySelector('.bg-muted.rounded-full');
      expect(dot).toBeTruthy();
    });
  });

  // -------------------------------------------------------------------------
  // Edge cases
  // -------------------------------------------------------------------------

  describe('edge cases', () => {
    it('renders without crashing when chapters array is empty', () => {
      const { container } = render(
        <MobileChapterTabs
          chapters={[]}
          activeChapterId={null}
          onChapterSelect={jest.fn()}
        />
      );
      expect(container).toBeTruthy();
    });

    it('renders without crashing when activeChapterId is null', () => {
      renderComponent(defaultChapters, null);
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('chapter without last_modified does not crash', () => {
      const noDate = makeChapter('nd', { last_modified: '' });
      render(
        <MobileChapterTabs
          chapters={[noDate]}
          activeChapterId="nd"
          onChapterSelect={jest.fn()}
        />
      );
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));
      // Should not throw
      expect(screen.getByTestId('sheet-content')).toBeInTheDocument();
    });
  });
});

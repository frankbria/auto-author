import { render, screen, fireEvent } from '@testing-library/react';
import TabContextMenu from '@/components/chapters/TabContextMenu';
import { ChapterStatus } from '@/types/chapter-tabs';

// HugeiconsIcon renders SVGs; stub so tests stay fast and focused on behaviour.
jest.mock('@hugeicons/react', () => ({
  HugeiconsIcon: () => null,
}));
jest.mock('@hugeicons/core-free-icons', () => ({
  MoreVerticalIcon: {},
  Edit01Icon: {},
  Delete02Icon: {},
  Copy01Icon: {},
  ViewIcon: {},
}));

// ---------------------------------------------------------------------------
// Tests preserved from the original file
// ---------------------------------------------------------------------------

describe('TabContextMenu Edit action', () => {
  it('renders nothing without a chapterId', () => {
    const { container } = render(<TabContextMenu onEdit={jest.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('calls onEdit with the chapterId when Edit is clicked', () => {
    const onEdit = jest.fn();
    render(<TabContextMenu chapterId="ch-1" onEdit={onEdit} />);

    // Open the menu
    fireEvent.click(screen.getByRole('button'));
    fireEvent.click(screen.getByText('Edit'));

    expect(onEdit).toHaveBeenCalledWith('ch-1');
  });

  it('hides the Edit button when no onEdit handler is provided', () => {
    render(<TabContextMenu chapterId="ch-1" />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.queryByText('Edit')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Expanded tests
// ---------------------------------------------------------------------------

describe('TabContextMenu', () => {
  // -------------------------------------------------------------------------
  // Open / close toggle
  // -------------------------------------------------------------------------

  describe('open / close behaviour', () => {
    it('does not show the menu initially', () => {
      render(<TabContextMenu chapterId="ch-1" />);
      expect(screen.queryByText('Mark as Draft')).not.toBeInTheDocument();
    });

    it('shows the menu when the trigger button is clicked', () => {
      render(<TabContextMenu chapterId="ch-1" />);
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));
      expect(screen.getByText('Mark as Draft')).toBeInTheDocument();
    });

    it('closes the menu when the backdrop overlay is clicked', () => {
      render(<TabContextMenu chapterId="ch-1" />);
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));
      expect(screen.getByText('Mark as Draft')).toBeInTheDocument();

      // The overlay is the fixed inset-0 div rendered behind the menu
      const overlay = document.querySelector('.fixed.inset-0');
      expect(overlay).not.toBeNull();
      fireEvent.click(overlay!);

      expect(screen.queryByText('Mark as Draft')).not.toBeInTheDocument();
    });

    it('toggles aria-expanded on the trigger button', () => {
      render(<TabContextMenu chapterId="ch-1" />);
      const trigger = screen.getByRole('button', { name: /chapter options/i });

      expect(trigger).toHaveAttribute('aria-expanded', 'false');
      fireEvent.click(trigger);
      expect(trigger).toHaveAttribute('aria-expanded', 'true');
      fireEvent.click(trigger);
      expect(trigger).toHaveAttribute('aria-expanded', 'false');
    });
  });

  // -------------------------------------------------------------------------
  // handleStatusUpdate — all four status variants
  // -------------------------------------------------------------------------

  describe('handleStatusUpdate', () => {
    const openMenu = (chapterId = 'ch-99') => {
      render(
        <TabContextMenu
          chapterId={chapterId}
          onStatusUpdate={onStatusUpdate}
        />
      );
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));
    };

    let onStatusUpdate: jest.Mock;

    beforeEach(() => {
      onStatusUpdate = jest.fn();
    });

    it('calls onStatusUpdate with DRAFT status and closes menu', () => {
      openMenu();
      fireEvent.click(screen.getByText('Mark as Draft'));
      expect(onStatusUpdate).toHaveBeenCalledWith('ch-99', ChapterStatus.DRAFT);
      expect(screen.queryByText('Mark as Draft')).not.toBeInTheDocument();
    });

    it('calls onStatusUpdate with IN_PROGRESS status and closes menu', () => {
      openMenu();
      fireEvent.click(screen.getByText('Mark as In Progress'));
      expect(onStatusUpdate).toHaveBeenCalledWith('ch-99', ChapterStatus.IN_PROGRESS);
      expect(screen.queryByText('Mark as In Progress')).not.toBeInTheDocument();
    });

    it('calls onStatusUpdate with COMPLETED status and closes menu', () => {
      openMenu();
      fireEvent.click(screen.getByText('Mark as Completed'));
      expect(onStatusUpdate).toHaveBeenCalledWith('ch-99', ChapterStatus.COMPLETED);
      expect(screen.queryByText('Mark as Completed')).not.toBeInTheDocument();
    });

    it('calls onStatusUpdate with PUBLISHED status and closes menu', () => {
      openMenu();
      fireEvent.click(screen.getByText('Mark as Published'));
      expect(onStatusUpdate).toHaveBeenCalledWith('ch-99', ChapterStatus.PUBLISHED);
      expect(screen.queryByText('Mark as Published')).not.toBeInTheDocument();
    });

    it('does not throw when onStatusUpdate is not provided', () => {
      render(<TabContextMenu chapterId="ch-1" />);
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));
      expect(() => {
        fireEvent.click(screen.getByText('Mark as Draft'));
      }).not.toThrow();
    });
  });

  // -------------------------------------------------------------------------
  // handleAction — delete
  // -------------------------------------------------------------------------

  describe('handleAction for delete', () => {
    it('calls onDelete with chapterId and closes menu', () => {
      const onDelete = jest.fn();
      render(<TabContextMenu chapterId="ch-5" onDelete={onDelete} />);
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));

      expect(screen.getByText('Delete')).toBeInTheDocument();
      fireEvent.click(screen.getByText('Delete'));

      expect(onDelete).toHaveBeenCalledWith('ch-5');
      expect(screen.queryByText('Delete')).not.toBeInTheDocument();
    });

    it('hides Delete button when onDelete is not provided', () => {
      render(<TabContextMenu chapterId="ch-5" />);
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));
      expect(screen.queryByText('Delete')).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // handleAction — preview
  // -------------------------------------------------------------------------

  describe('handleAction for preview', () => {
    it('calls onPreview with chapterId and closes menu', () => {
      const onPreview = jest.fn();
      render(<TabContextMenu chapterId="ch-7" onPreview={onPreview} />);
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));

      expect(screen.getByText('Preview')).toBeInTheDocument();
      fireEvent.click(screen.getByText('Preview'));

      expect(onPreview).toHaveBeenCalledWith('ch-7');
      expect(screen.queryByText('Preview')).not.toBeInTheDocument();
    });

    it('hides Preview button when onPreview is not provided', () => {
      render(<TabContextMenu chapterId="ch-7" />);
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));
      expect(screen.queryByText('Preview')).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // handleAction — duplicate
  // -------------------------------------------------------------------------

  describe('handleAction for duplicate', () => {
    it('calls onDuplicate with chapterId and closes menu', () => {
      const onDuplicate = jest.fn();
      render(<TabContextMenu chapterId="ch-8" onDuplicate={onDuplicate} />);
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));

      expect(screen.getByText('Duplicate')).toBeInTheDocument();
      fireEvent.click(screen.getByText('Duplicate'));

      expect(onDuplicate).toHaveBeenCalledWith('ch-8');
      expect(screen.queryByText('Duplicate')).not.toBeInTheDocument();
    });

    it('hides Duplicate button when onDuplicate is not provided', () => {
      render(<TabContextMenu chapterId="ch-8" />);
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));
      expect(screen.queryByText('Duplicate')).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // All optional action buttons visible together
  // -------------------------------------------------------------------------

  describe('all optional actions', () => {
    it('shows all optional buttons when all handlers are provided', () => {
      render(
        <TabContextMenu
          chapterId="ch-all"
          onEdit={jest.fn()}
          onDelete={jest.fn()}
          onPreview={jest.fn()}
          onDuplicate={jest.fn()}
          onStatusUpdate={jest.fn()}
        />
      );
      fireEvent.click(screen.getByRole('button', { name: /chapter options/i }));

      expect(screen.getByText('Edit')).toBeInTheDocument();
      expect(screen.getByText('Delete')).toBeInTheDocument();
      expect(screen.getByText('Preview')).toBeInTheDocument();
      expect(screen.getByText('Duplicate')).toBeInTheDocument();
      expect(screen.getByText('Mark as Draft')).toBeInTheDocument();
    });
  });
});

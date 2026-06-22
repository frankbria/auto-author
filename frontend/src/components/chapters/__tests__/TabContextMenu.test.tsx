import { render, screen, fireEvent } from '@testing-library/react';
import TabContextMenu from '@/components/chapters/TabContextMenu';

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

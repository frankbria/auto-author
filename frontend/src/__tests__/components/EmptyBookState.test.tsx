import React from 'react';
import { render, screen } from '@testing-library/react';
import { EmptyBookState } from '@/components/EmptyBookState';

jest.mock('next/image', () => ({
  __esModule: true,
  // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
  default: ({ fill, priority, ...props }: any) => <img {...props} />,
}));

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, className }: any) => (
    <button onClick={onClick} className={className}>
      {children}
    </button>
  ),
}));

describe('EmptyBookState theme tokens (#206)', () => {
  it('uses theme tokens on the panel container', () => {
    render(<EmptyBookState onCreateNew={jest.fn()} />);

    const heading = screen.getByText('Start Your First Book');
    expect(heading).toHaveClass('text-foreground');
    const panel = heading.closest('div.rounded-xl');
    expect(panel).toHaveClass('bg-card/50', 'border-border');
  });

  it('uses muted tokens for body text and step cards', () => {
    render(<EmptyBookState onCreateNew={jest.fn()} />);

    expect(screen.getByText(/Create your first book project/)).toHaveClass(
      'text-muted-foreground'
    );
    expect(screen.getByText('Enter book details')).toHaveClass('text-muted-foreground');
    expect(screen.getByText('1. Create')).toHaveClass('text-foreground');
    expect(screen.getByText('1. Create').parentElement).toHaveClass('bg-muted/40');
  });

  it('uses the primary token pattern for the CTA button', () => {
    render(<EmptyBookState onCreateNew={jest.fn()} />);

    expect(screen.getByText('Create New Book')).toHaveClass(
      'bg-primary',
      'hover:bg-primary/90',
      'text-primary-foreground'
    );
  });

  it('contains no theme-independent gray/indigo color literals', () => {
    const { container } = render(<EmptyBookState onCreateNew={jest.fn()} />);

    for (const el of Array.from(container.querySelectorAll('[class]'))) {
      const themeIndependent = (el.getAttribute('class') ?? '')
        .split(/\s+/)
        .filter((cls) => !cls.startsWith('dark:'));
      for (const cls of themeIndependent) {
        expect(cls).not.toMatch(/(?:gray|indigo)-\d/);
      }
    }
  });
});

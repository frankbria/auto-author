/**
 * Tests for BookMetadataForm — focused on the save state (spinner + disabled
 * inputs) added for issue #52 (comprehensive loading indicators).
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BookMetadataForm } from '../BookMetadataForm';
import { BookFormData } from '@/lib/schemas/bookSchema';

const book: BookFormData = {
  title: 'My Book',
  subtitle: '',
  description: '',
  genre: 'fiction',
  target_audience: 'general',
  cover_image_url: '',
};

describe('BookMetadataForm genre taxonomy (shared with BookCreationWizard, #205)', () => {
  it('offers the full canonical genre list, not the old 7-item subset', () => {
    render(<BookMetadataForm book={book} onUpdate={jest.fn()} isSaving={false} />);
    // 'Historical' and 'Biography' exist only in the canonical (wizard) taxonomy;
    // the pre-#205 local list omitted them.
    expect(screen.getByRole('option', { name: 'Historical' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Biography' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Self-Help' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Business' })).toBeInTheDocument();
  });

  it('offers no fiction-only genres — Auto Author is nonfiction (#215)', () => {
    render(<BookMetadataForm book={book} onUpdate={jest.fn()} isSaving={false} />);
    for (const fiction of ['Fiction', 'Science Fiction', 'Fantasy', 'Mystery', 'Romance']) {
      expect(screen.queryByRole('option', { name: fiction })).not.toBeInTheDocument();
    }
  });
});

describe('BookMetadataForm saving state', () => {
  it('does not show the saving indicator when isSaving is false', () => {
    render(<BookMetadataForm book={book} onUpdate={jest.fn()} isSaving={false} />);
    expect(screen.queryByText('Saving...')).not.toBeInTheDocument();
    expect(screen.getByDisplayValue('My Book')).not.toBeDisabled();
  });

  it('shows a spinner + "Saving..." and disables inputs when isSaving is true', () => {
    render(<BookMetadataForm book={book} onUpdate={jest.fn()} isSaving={true} />);
    const status = screen.getByText('Saving...');
    expect(status).toBeInTheDocument();
    expect(status.closest('[role="status"]')).toHaveAttribute('aria-live', 'polite');
    // Title input is disabled during save
    expect(screen.getByDisplayValue('My Book')).toBeDisabled();
  });
});

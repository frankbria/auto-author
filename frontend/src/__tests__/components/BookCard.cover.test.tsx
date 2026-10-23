import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import BookCard, { BookProject } from '@/components/BookCard';

jest.mock('next/navigation', () => ({ useRouter: () => ({ push: jest.fn() }) }));

/** The dashboard card shows the cover thumbnail when the book has one (#941). */

const book: BookProject = { id: 'b1', title: 'Covered', chapters: 0, progress: 0 };

it('shows the cover thumbnail, resolved against the API origin', () => {
  render(
    <BookCard
      book={{
        ...book,
        cover_image_url: '/uploads/cover_images/b1_c.jpg',
        cover_thumbnail_url: '/uploads/cover_images/b1_c_thumb.jpg',
      }}
    />,
  );
  expect(screen.getByRole('img', { name: /cover of covered/i })).toHaveAttribute(
    'src',
    'http://localhost:8000/uploads/cover_images/b1_c_thumb.jpg',
  );
});

it('shows no image for a book without a cover', () => {
  render(<BookCard book={book} />);
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
});

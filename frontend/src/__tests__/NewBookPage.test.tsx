import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import NewBook from '@/app/dashboard/new-book/page';
import bookClient from '@/lib/api/bookClient';
import { showErrorNotification } from '@/components/errors';
import { toast } from '@/lib/toast';

const push = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}));

jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: { createBook: jest.fn() },
}));

jest.mock('@/components/errors', () => ({
  showErrorNotification: jest.fn(),
}));

jest.mock('@/lib/toast', () => ({
  toast: { success: jest.fn() },
}));

const createBook = bookClient.createBook as jest.Mock;

function fillRequired() {
  fireEvent.change(screen.getByLabelText(/Book Title/i), { target: { value: 'My Book' } });
  fireEvent.change(screen.getByLabelText(/Genre/i), { target: { value: 'business' } });
  fireEvent.change(screen.getByLabelText(/Target Audience/i), { target: { value: 'Everyone' } });
}

describe('NewBook page error/success feedback', () => {
  beforeEach(() => jest.clearAllMocks());

  it('shows a success toast and redirects when creation succeeds', async () => {
    createBook.mockResolvedValueOnce({ id: 'book-123' });
    render(<NewBook />);
    fillRequired();
    fireEvent.click(screen.getByRole('button', { name: /create book/i }));

    await waitFor(() => expect(toast.success).toHaveBeenCalled());
    expect(push).toHaveBeenCalledWith('/dashboard/books/book-123');
  });

  it('shows an error notification and does not redirect when creation fails', async () => {
    createBook.mockRejectedValueOnce(new Error('boom'));
    render(<NewBook />);
    fillRequired();
    fireEvent.click(screen.getByRole('button', { name: /create book/i }));

    await waitFor(() => expect(showErrorNotification).toHaveBeenCalled());
    expect(push).not.toHaveBeenCalled();
  });
});

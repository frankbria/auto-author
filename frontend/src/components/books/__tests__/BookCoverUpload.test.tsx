import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BookCoverUpload } from '../BookCoverUpload';
import { toast } from '@/lib/toast';

jest.mock('@/lib/toast', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

function makeFile(type: string, size: number, name = 'cover.jpg') {
  const file = new File(['x'], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
}

function answer(status: number, body: unknown) {
  (global.fetch as jest.Mock).mockResolvedValue({
    ok: status < 400,
    status,
    json: async () => body,
  });
}

const choose = (file: File) =>
  fireEvent.change(screen.getByLabelText(/upload book cover/i), { target: { files: [file] } });

describe('BookCoverUpload (#941)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();
  });

  it('shows a local cover from the API origin, unoptimized', () => {
    render(<BookCoverUpload bookId="b1" coverUrl="/uploads/cover_images/b1_x.jpg" onUploaded={jest.fn()} />);
    const img = screen.getByRole('img', { name: /book cover/i });
    expect(img).toHaveAttribute('src', 'http://localhost:8000/uploads/cover_images/b1_x.jpg');
    expect(screen.getByRole('button', { name: /change cover/i })).toBeInTheDocument();
  });

  it('offers an upload when there is no cover', () => {
    render(<BookCoverUpload bookId="b1" coverUrl={undefined} onUploaded={jest.fn()} />);
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload cover/i })).toHaveAccessibleDescription(
      /jpeg, png, webp or gif, up to 5mb/i,
    );
  });

  it('rejects an invalid file type without uploading', () => {
    render(<BookCoverUpload bookId="b1" coverUrl={undefined} onUploaded={jest.fn()} />);
    choose(makeFile('text/plain', 100, 'a.txt'));
    expect(toast.error).toHaveBeenCalled();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('rejects a file over 5MB without uploading', () => {
    render(<BookCoverUpload bookId="b1" coverUrl={undefined} onUploaded={jest.fn()} />);
    choose(makeFile('image/jpeg', 5 * 1024 * 1024 + 1));
    expect(toast.error).toHaveBeenCalled();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('posts the file to the book cover route and reports both URLs', async () => {
    answer(200, {
      cover_image_url: '/uploads/cover_images/b1_c.jpg',
      cover_thumbnail_url: '/uploads/cover_images/b1_t_thumb.jpg',
    });
    const onUploaded = jest.fn();
    render(<BookCoverUpload bookId="b1" coverUrl={undefined} onUploaded={onUploaded} />);
    choose(makeFile('image/png', 1000, 'c.png'));

    await waitFor(() =>
      expect(onUploaded).toHaveBeenCalledWith({
        cover_image_url: '/uploads/cover_images/b1_c.jpg',
        cover_thumbnail_url: '/uploads/cover_images/b1_t_thumb.jpg',
      }),
    );
    const [url, opts] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toBe('http://localhost:8000/api/v1/books/b1/cover-image');
    expect(opts.method).toBe('POST');
    expect(opts.credentials).toBe('include');
    expect(opts.body).toBeInstanceOf(FormData);
    expect(toast.success).toHaveBeenCalled();
  });

  it.each([
    [429, { detail: 'Rate limit exceeded. Try again in 42 seconds.' }, 'Rate limit exceeded. Try again in 42 seconds.'],
    [400, { detail: 'Invalid image file' }, 'Invalid image file'],
    [422, { detail: [{ loc: ['body', 'file'], msg: 'field required', type: 'missing' }] }, 'field required'],
  ])('shows the %s message', async (status, body, message) => {
    answer(status, body);
    const onUploaded = jest.fn();
    render(<BookCoverUpload bookId="b1" coverUrl={undefined} onUploaded={onUploaded} />);
    choose(makeFile('image/jpeg', 1000));

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    expect((toast.error as jest.Mock).mock.calls.at(-1)![0].description).toBe(message);
    expect(onUploaded).not.toHaveBeenCalled();
  });

  it('clears the input after a rejected file, so picking it again fires change', () => {
    const setValue = jest.spyOn(HTMLInputElement.prototype, 'value', 'set');
    render(<BookCoverUpload bookId="b1" coverUrl={undefined} onUploaded={jest.fn()} />);
    choose(makeFile('text/plain', 100, 'a.txt'));
    expect(setValue).toHaveBeenCalledWith('');
    setValue.mockRestore();
  });

  it('keeps the button focusable while uploading, and ignores clicks on it', async () => {
    (global.fetch as jest.Mock).mockReturnValue(new Promise(() => {}));
    render(<BookCoverUpload bookId="b1" coverUrl={undefined} onUploaded={jest.fn()} />);
    const button = screen.getByRole('button', { name: /upload cover/i });
    button.focus();
    choose(makeFile('image/png', 1000, 'c.png'));

    const busy = await screen.findByRole('button', { name: /uploading/i });
    expect(busy).toBe(button);
    expect(busy).not.toBeDisabled();
    expect(busy).toHaveAttribute('aria-disabled', 'true');
    expect(busy).toHaveFocus();

    const pick = jest.spyOn(screen.getByLabelText(/upload book cover/i) as HTMLInputElement, 'click');
    fireEvent.click(busy);
    expect(pick).not.toHaveBeenCalled();
  });
});

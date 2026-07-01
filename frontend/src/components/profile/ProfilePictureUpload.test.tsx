import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ProfilePictureUpload } from './ProfilePictureUpload';
import useOptimizedClerkImage from '@/hooks/useOptimizedClerkImage';
import { toast } from '@/lib/toast';

jest.mock('@/hooks/useOptimizedClerkImage');
jest.mock('@/lib/toast', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('next/image', () => ({
  __esModule: true,
  default: ({ src, alt }: { src: string; alt: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} data-testid="image" />
  ),
}));

function makeFile(type: string, size: number, name = 'avatar.jpg') {
  const file = new File(['x'], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
}

describe('ProfilePictureUpload', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useOptimizedClerkImage as jest.Mock).mockReturnValue({
      getOptimizedImageUrl: (url: string) => url,
    });
    global.fetch = jest.fn();
  });

  it('renders the current avatar and a change button', () => {
    render(<ProfilePictureUpload currentAvatarUrl="https://x/avatar.jpg" onUploaded={jest.fn()} />);
    expect(screen.getByTestId('image')).toHaveAttribute('src', expect.stringContaining('avatar.jpg'));
    expect(screen.getByRole('button', { name: /change photo/i })).toBeInTheDocument();
  });

  it('rejects an invalid file type without uploading', () => {
    render(<ProfilePictureUpload currentAvatarUrl={null} onUploaded={jest.fn()} />);
    const input = screen.getByTestId('avatar-input');
    fireEvent.change(input, { target: { files: [makeFile('text/plain', 100, 'a.txt')] } });
    expect(toast.error).toHaveBeenCalled();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('rejects a file over 5MB without uploading', () => {
    render(<ProfilePictureUpload currentAvatarUrl={null} onUploaded={jest.fn()} />);
    const input = screen.getByTestId('avatar-input');
    fireEvent.change(input, { target: { files: [makeFile('image/jpeg', 5 * 1024 * 1024 + 1)] } });
    expect(toast.error).toHaveBeenCalled();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('uploads a valid file and reports the new url', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ avatar_url: '/uploads/profile_pictures/new.jpg' }),
    });
    const onUploaded = jest.fn();
    render(<ProfilePictureUpload currentAvatarUrl={null} onUploaded={onUploaded} />);
    fireEvent.change(screen.getByTestId('avatar-input'), {
      target: { files: [makeFile('image/jpeg', 1000)] },
    });
    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith('/uploads/profile_pictures/new.jpg'));
    const [url, opts] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toContain('/users/me/avatar');
    expect(opts.method).toBe('POST');
    expect(opts.credentials).toBe('include');
    expect(opts.body).toBeInstanceOf(FormData);
    expect(toast.success).toHaveBeenCalled();
  });

  it('shows an error toast when the upload fails', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      json: async () => ({ detail: 'boom' }),
    });
    render(<ProfilePictureUpload currentAvatarUrl={null} onUploaded={jest.fn()} />);
    fireEvent.change(screen.getByTestId('avatar-input'), {
      target: { files: [makeFile('image/jpeg', 1000)] },
    });
    await waitFor(() => expect(toast.error).toHaveBeenCalled());
  });
});

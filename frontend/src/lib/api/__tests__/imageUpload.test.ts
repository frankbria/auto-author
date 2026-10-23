import { uploadUrl } from '../imageUpload';

describe('uploadUrl (#941)', () => {
  it('resolves a local-storage path against the API origin, not the page', () => {
    expect(uploadUrl('/uploads/cover_images/a_b.jpg')).toBe(
      'http://localhost:8000/uploads/cover_images/a_b.jpg',
    );
  });

  it('leaves a cloud URL unchanged', () => {
    const url = 'https://bkt.s3.us-east-1.amazonaws.com/cover_images/a/b.jpg';
    expect(uploadUrl(url)).toBe(url);
  });

  it('leaves a protocol-relative URL alone instead of treating it as local', () => {
    expect(uploadUrl('//evil.test/x.jpg')).toBe('//evil.test/x.jpg');
  });

  it('gives nothing for no URL', () => {
    expect(uploadUrl(null)).toBeUndefined();
    expect(uploadUrl(undefined)).toBeUndefined();
    expect(uploadUrl('')).toBeUndefined();
  });
});

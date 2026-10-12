/** @jest-environment node */
import nextConfig from '../../next.config';

describe('next.config headers (#772)', () => {
  it('allows the microphone for our own origin only; camera and geolocation stay off', async () => {
    const rules = await nextConfig.headers!();
    const all = rules.find((r) => r.source === '/(.*)')!;
    const policy = all.headers.find((h) => h.key === 'Permissions-Policy')!.value;
    expect(policy).toBe('camera=(), microphone=(self), geolocation=()');
  });
});

describe('next.config headers (#814)', () => {
  it('tells the browser to keep using https', async () => {
    const rules = await nextConfig.headers!();
    const all = rules.find((r) => r.source === '/(.*)')!;
    const hsts = all.headers.find((h) => h.key === 'Strict-Transport-Security');
    expect(hsts?.value).toBe('max-age=31536000');
  });

  it('does not name the framework in X-Powered-By', () => {
    expect(nextConfig.poweredByHeader).toBe(false);
  });
});

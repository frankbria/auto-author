import { getIP } from '@better-auth/core/utils/ip';

import { getIpAddressConfig } from '@/lib/auth-ip';

// The real resolver from better-auth, driven with our config — a config-shape
// assertion would not have caught #602, since the bug was in what getIP() does
// with the default header set behind nginx.
const resolve = (headers: Record<string, string>) =>
  getIP(new Headers(headers), { advanced: { ipAddress: getIpAddressConfig() } });

describe('better-auth client IP resolution (issue #602)', () => {
  it('resolves the real client IP even when the request carries a spoofed X-Forwarded-For', () => {
    // nginx appends $remote_addr to any client-supplied XFF
    // ($proxy_add_x_forwarded_for), so an attacker turns the chain multi-hop.
    // X-Real-IP is proxy_set_header'd from $remote_addr and cannot be poisoned.
    expect(
      resolve({
        'x-forwarded-for': '203.0.113.7, 198.51.100.9',
        'x-real-ip': '198.51.100.9',
      }),
    ).toBe('198.51.100.9');
  });

  it('gives two different clients two different rate-limit buckets despite identical spoofing', () => {
    const attacker = resolve({
      'x-forwarded-for': '203.0.113.7, 192.0.2.10',
      'x-real-ip': '192.0.2.10',
    });
    const victim = resolve({
      'x-forwarded-for': '203.0.113.7, 192.0.2.20',
      'x-real-ip': '192.0.2.20',
    });

    expect(attacker).toBe('192.0.2.10');
    expect(victim).toBe('192.0.2.20');
    expect(attacker).not.toBe(victim);
  });

  it('falls back to X-Forwarded-For where no proxy sets X-Real-IP', () => {
    expect(resolve({ 'x-forwarded-for': '198.51.100.9' })).toBe('198.51.100.9');
  });

  it('prefers X-Real-IP over a single-hop X-Forwarded-For', () => {
    expect(
      resolve({ 'x-forwarded-for': '203.0.113.7', 'x-real-ip': '198.51.100.9' }),
    ).toBe('198.51.100.9');
  });

  it('keeps IP tracking enabled so the limiter still buckets per client', () => {
    expect(getIpAddressConfig().disableIpTracking).not.toBe(true);
  });
});

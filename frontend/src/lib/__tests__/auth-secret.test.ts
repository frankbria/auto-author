import { createHash } from 'crypto';
import { assertSecretNotPublished, PUBLISHED_SECRET_SHA256 } from '@/lib/auth-secret';

// Only hashes of published secrets exist in the code; use a synthetic stand-in.
const STAND_IN = 'Zx9-stand-in-published-secret-0123456789ab';

const run = (env: Record<string, string>) =>
  assertSecretNotPublished({ BETTER_AUTH_SECRET: STAND_IN, ...env } as unknown as NodeJS.ProcessEnv);

describe('assertSecretNotPublished (#780)', () => {
  beforeAll(() => {
    PUBLISHED_SECRET_SHA256.add(createHash('sha256').update(STAND_IN).digest('hex'));
  });

  it.each(['staging', 'production'])('throws on %s without echoing the value', (ENVIRONMENT) => {
    let message = '';
    try {
      run({ ENVIRONMENT });
    } catch (e) {
      message = (e as Error).message;
    }
    expect(message).toContain('published');
    expect(message).not.toContain(STAND_IN);
  });

  it('throws when NODE_ENV=production', () => {
    expect(() => run({ NODE_ENV: 'production' })).toThrow();
  });

  it('allows development', () => {
    expect(() => run({ ENVIRONMENT: 'development', NODE_ENV: 'development' })).not.toThrow();
  });

  it('allows a rotated secret on staging', () => {
    expect(() => run({ BETTER_AUTH_SECRET: 'a-freshly-rotated-secret', ENVIRONMENT: 'staging' })).not.toThrow();
  });
});

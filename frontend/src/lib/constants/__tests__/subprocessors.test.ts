import { readdirSync, readFileSync } from 'fs';
import { join } from 'path';
import { SUBPROCESSORS } from '@/lib/constants/subprocessors';
import { FRONTEND_ROOT, shippedSources } from '@/__tests__/theme/helpers/sources';

/**
 * #788: the privacy policy named no recipients while the app sent data to seven
 * of them. Tripwire: a third-party integration arrives with a credential or an
 * endpoint, so every setting shaped like one must be claimed by a subprocessor
 * entry. A new one fails here until the policy names who receives the data.
 */
const CREDENTIAL = /_(KEY|KEY_ID|SECRET|DSN|URI|URL|TOKEN|PASSWORD)$/;

// Sent to no one: our own signing secret and our own origins.
const FIRST_PARTY = [
  'BETTER_AUTH_SECRET',
  'BETTER_AUTH_URL',
  'NEXT_PUBLIC_BETTER_AUTH_URL',
  'NEXT_PUBLIC_API_URL',
];

const BACKEND_APP = join(FRONTEND_ROOT, '..', 'backend/app');

const backendSettings = [
  ...readFileSync(join(BACKEND_APP, 'core/config.py'), 'utf8').matchAll(/^ {4}([A-Z][A-Z0-9_]+):/gm),
].map((m) => m[1]);

// Reads that bypass Settings are swept too. cloud_storage_service.py did until
// #806, and the seed script until #851; main.py still reads ENVIRONMENT this way.
const backendEnv = (readdirSync(BACKEND_APP, { recursive: true }) as string[])
  .filter((file) => file.endsWith('.py'))
  .flatMap((file) =>
    [
      ...readFileSync(join(BACKEND_APP, file), 'utf8').matchAll(
        /os\.(?:getenv\(|environ\.get\(|environ\[)\s*["']([A-Z0-9_]+)/g
      ),
    ].map((m) => m[1])
  );

const frontendEnv = shippedSources().flatMap((file) =>
  [
    ...readFileSync(join(FRONTEND_ROOT, file), 'utf8').matchAll(
      /process\.env(?:\.|\[['"])([A-Z0-9_]+)/g
    ),
  ].map((m) => m[1])
);

const configured = [...new Set([...backendSettings, ...backendEnv, ...frontendEnv])];
const credentials = configured.filter((key) => CREDENTIAL.test(key));
const claimed = SUBPROCESSORS.flatMap((s) => s.envKeys);

describe('subprocessor inventory (#788)', () => {
  it('finds the settings it is meant to sweep', () => {
    expect(backendSettings).toContain('STRIPE_SECRET_KEY');
    expect(backendSettings).toContain('CLOUDINARY_API_SECRET');
    expect(backendEnv).toContain('ENVIRONMENT');
    expect(frontendEnv).toContain('EMAIL_SERVICE_API_KEY');
    expect(credentials.length).toBeGreaterThan(FIRST_PARTY.length);
  });

  it('maps every credential in config/env to a named subprocessor', () => {
    expect(credentials.filter((key) => !claimed.includes(key) && !FIRST_PARTY.includes(key))).toEqual(
      []
    );
  });

  it('claims no setting that no longer exists', () => {
    expect([...claimed, ...FIRST_PARTY].filter((key) => !configured.includes(key))).toEqual([]);
  });

  it('gives every entry a name, a purpose and the data it receives', () => {
    expect(SUBPROCESSORS.length).toBeGreaterThan(0);
    for (const s of SUBPROCESSORS) {
      expect([s.name, s.purpose, s.data].every((field) => field.trim().length > 0)).toBe(true);
    }
    expect(new Set(SUBPROCESSORS.map((s) => s.name)).size).toBe(SUBPROCESSORS.length);
  });
});

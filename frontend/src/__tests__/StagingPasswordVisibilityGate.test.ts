import { readdirSync, readFileSync } from 'fs';
import { join } from 'path';

/**
 * #604, residual from #599. Staging E2E screenshots and video are still uploaded
 * as CI artifacts on a **public** repository. That is only safe because the
 * password field renders masked — and the sign-in page has a show-password
 * toggle:
 *
 *   src/app/auth/sign-in/page.tsx
 *     type={showPassword ? "text" : "password"}
 *     aria-label={showPassword ? "Hide password" : "Show password"}
 *
 * No staging spec clicks it today, so the invariant holds. Nothing enforced it:
 * a spec that toggled visibility — to assert the feature works, or incidentally
 * while debugging a selector — would publish the account password into every
 * screenshot and video frame taken after the click, silently and permanently,
 * on a repo anyone can read.
 *
 * #599's README warns about this. A warning is not a control. This is the
 * control.
 *
 * Deliberately a **tripwire, not a proof**, in the same terms #604 uses for the
 * other jest guards: it catches the accidental case — someone reaching for the
 * toggle in a staging spec — not a determined edit that renames the label or
 * drives the click through an indirection. Strengthening past that would need
 * the artifact itself inspected, which is #604's first acceptance criterion and
 * needs a real failing staging run.
 */

const STAGING_SPECS = join(__dirname, '..', '..', 'tests', 'e2e', 'staging');

/** Every `.ts` under the staging spec tree, including fixtures and helpers. */
function stagingSources(dir: string = STAGING_SPECS): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      // Playwright's own output dirs are not source and churn constantly.
      if (['test-results', 'playwright-report-staging'].includes(entry.name)) return [];
      return stagingSources(path);
    }
    return entry.name.endsWith('.ts') ? [path] : [];
  });
}

/**
 * Ways a spec could unmask the password field.
 *
 * Matched against source text rather than behaviour: the point is to fail in
 * review, before a run ever uploads anything.
 */
const UNMASK_PATTERNS: ReadonlyArray<readonly [string, RegExp]> = [
  ['the toggle by its aria-label', /['"`]\s*(show|hide) password\s*['"`]/i],
  ['the toggle by label lookup', /getByLabel\((?:[^)]*)(show|hide)\s+password/i],
  ['the component state directly', /showPassword/],
  // The comma matters: `toHaveAttribute('type', 'text')` is the commonest shape,
  // and a class without `,` silently misses it — which is how the first cut of
  // this pattern passed its own fixture test.
  ['asserting the field is unmasked', /password[^\n]{0,60}type['"`\s:=,]+['"`]text['"`]/i],
];

describe('staging specs never unmask the password field (#604)', () => {
  const sources = stagingSources();

  it('sweeps the staging spec tree', () => {
    // Vacuity guard. If the walk stops finding files, every assertion below
    // passes over an empty set forever — the exact shape #613 was about.
    expect(sources.length).toBeGreaterThanOrEqual(4);
    expect(sources.map((p) => p.split('/').pop())).toEqual(
      expect.arrayContaining(['complete-user-journey.spec.ts', 'regressions.spec.ts'])
    );
  });

  it('recognises an unmasking spec and clears a normal one', () => {
    // Anti-vacuity: pins the patterns to fixtures, so a typo in one of them
    // cannot quietly turn this file green while the tree is unguarded.
    const offending = (source: string) =>
      UNMASK_PATTERNS.filter(([, pattern]) => pattern.test(source)).map(([label]) => label);

    expect(offending(`await page.getByLabel('Show password').click();`)).toContain(
      'the toggle by its aria-label'
    );
    expect(offending(`await page.click('[aria-label="Hide password"]');`)).toContain(
      'the toggle by its aria-label'
    );
    expect(offending(`expect(showPassword).toBe(true)`)).toContain(
      'the component state directly'
    );
    expect(offending(`await expect(password).toHaveAttribute('type', 'text')`)).toContain(
      'asserting the field is unmasked'
    );

    // The normal shape a staging spec uses — must not trip.
    expect(offending(`await page.fill('#password', process.env.STAGING_TEST_PASSWORD!)`)).toEqual(
      []
    );
    expect(offending(`await expect(password).toHaveAttribute('type', 'password')`)).toEqual([]);
  });

  it('no staging spec unmasks the password field', () => {
    const offenders = sources.flatMap((path) => {
      const source = readFileSync(path, 'utf8');
      return UNMASK_PATTERNS.filter(([, pattern]) => pattern.test(source)).map(
        ([label]) => `${path.split('/staging/')[1]} :: ${label}`
      );
    });

    expect(offenders).toEqual([]);
  });
});

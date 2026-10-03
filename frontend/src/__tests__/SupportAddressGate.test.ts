import { execFileSync } from 'child_process';
import { join } from 'path';
import { SUPPORT_EMAIL } from '@/lib/constants/contact';

/**
 * #773: the published support address once pointed at autoauthor.com, a parked
 * domain with no MX record, so privacy requests and 2FA-recovery mail bounced.
 * The product's domain is autoauthor.app. Tripwire: the dead domain must not
 * reappear anywhere in frontend/src, and the address lives in one constant.
 */
const SRC = join(__dirname, '..');
const SELF = 'SupportAddressGate.test.ts';

function grep(pattern: string): string[] {
  try {
    return execFileSync('git', ['grep', '-nIE', pattern, '--', SRC], { encoding: 'utf8' })
      .split('\n')
      .filter((l) => l && !l.includes(SELF));
  } catch (e) {
    // Exit 1 is git-grep's "no match". Anything else (no git, not a repo) must
    // fail the guard rather than pass it vacuously.
    if ((e as { status?: number }).status === 1) return [];
    throw e;
  }
}

describe('support address (#773)', () => {
  it('uses the product domain', () => {
    expect(SUPPORT_EMAIL).toBe('support@autoauthor.app');
  });

  it('never references the parked autoauthor.com domain in frontend/src', () => {
    expect(grep('autoauthor\\.com')).toEqual([]);
  });

  it('hardcodes the address nowhere outside the constant', () => {
    expect(grep('support@autoauthor').filter((l) => !l.includes('constants/contact.ts'))).toEqual(
      []
    );
  });
});

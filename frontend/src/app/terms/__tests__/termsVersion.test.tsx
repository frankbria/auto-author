/**
 * The Terms copy and TERMS_VERSION change together (#961).
 *
 * New accounts record TERMS_VERSION as the version they accepted (#789). Editing
 * the copy without bumping it would record the old version against new text, so
 * the rendered text is pinned to the version here.
 *
 * Changed the Terms on purpose? Set TERMS_VERSION in src/lib/constants/legal.ts
 * to today's date, then set RECORDED below to that version and the digest this
 * test prints.
 */
import { createHash } from 'crypto';
import { render } from '@testing-library/react';
import TermsPage from '@/app/terms/page';
import { TERMS_VERSION } from '@/lib/constants/legal';

const RECORDED = {
  version: '2026-10-10',
  digest: '72c35d30002038dceaef7f2252207660301cf7446c8790f387c5fe52f3998a91',
};

function termsDigest(): string {
  const { container } = render(<TermsPage />);
  const text = (container.querySelector('main')?.textContent ?? '')
    .replace(/\s+/g, ' ')
    .trim();
  return createHash('sha256').update(text).digest('hex');
}

it('pins the rendered Terms to TERMS_VERSION (#961)', () => {
  const digest = termsDigest();
  expect({ version: TERMS_VERSION, digest }).toEqual(RECORDED);
});

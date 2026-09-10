import { readdirSync } from 'fs';
import { join, relative, sep } from 'path';

/**
 * The shipped-source walk shared by the static theme guards (#620, #632).
 *
 * Extracted from `core-authoring-pages-tokens.test.ts`, where #620 replaced a
 * hand-maintained page list with a whole-tree sweep. Sharing the walk is the
 * point: two guards over two hand-rolled file lists can disagree about what
 * "shipped" means, and the file that falls into the gap is exactly the one that
 * ships the bug (which is how #618 got in).
 */

export const FRONTEND_ROOT = join(__dirname, '..', '..', '..', '..');

const SRC_ROOT = join(FRONTEND_ROOT, 'src');

/**
 * Test sources are out of scope for every guard that uses this walk: they are
 * not shipped UI, several legitimately assert on the class names being banned,
 * and each guard's own doc comment quotes the pattern it bans — so a sweep that
 * included tests would match itself and fail the moment it was tracked.
 */
const IS_TEST_SOURCE = /(^|[\\/])(__tests__|__mocks__|e2e)[\\/]|\.(test|spec)\.[jt]sx?$/;
const IS_SOURCE = /\.tsx?$/;

/** Every shipped `.ts`/`.tsx` under `src/`, repo-relative and POSIX-separated. */
export function shippedSources(dir: string = SRC_ROOT): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const absolute = join(dir, entry.name);
    const relativePath = relative(FRONTEND_ROOT, absolute).split(sep).join('/');

    if (entry.isDirectory()) return shippedSources(absolute);
    if (!IS_SOURCE.test(entry.name)) return [];
    if (IS_TEST_SOURCE.test(relativePath)) return [];
    return [relativePath];
  });
}

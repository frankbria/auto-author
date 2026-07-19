/**
 * Dev-only console logger.
 *
 * `logger.debug` is silenced in production builds so internal client state never
 * ships to the user's browser. Next.js statically inlines `process.env.NODE_ENV`
 * at build time, so the guarded `console.log` is dead-code-eliminated from the
 * production bundle entirely.
 *
 * For genuine errors/warnings that SHOULD surface in production, keep using
 * `console.error` / `console.warn` directly.
 */
export const logger = {
  debug: (...args: unknown[]): void => {
    if (process.env.NODE_ENV !== 'production') {
      console.log(...args);
    }
  },
};

// jest.config.cjs
const nextJest = require('next/jest')

const createJestConfig = nextJest({
  dir: './',
})

const customJestConfig = {
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    // Mock better-auth to avoid ESM issues
    '^better-auth/client$': '<rootDir>/src/__mocks__/better-auth-client.ts',
    '^better-auth/client/plugins$': '<rootDir>/src/__mocks__/better-auth-client-plugins.ts',
    '^better-auth/react$': '<rootDir>/src/__mocks__/better-auth-react.ts',
    '^better-auth/api$': '<rootDir>/src/__mocks__/better-auth-api.ts',
    // Mock the Sentry SDK (#334) so tests stay deterministic and off the wire.
    '^@sentry/nextjs$': '<rootDir>/src/__mocks__/sentry-nextjs.ts',
  },
  testPathIgnorePatterns: [
    '<rootDir>/src/e2e/',
    '<rootDir>/e2e/',                    // Exclude Playwright E2E tests
    '.spec.ts',                          // Exclude Playwright spec files
    'responsive.spec.ts',                // Exclude Playwright E2E specs
  ],
  // Every source file counts, whether a test imports it or not (#842). Without
  // this, coverage measured only the files the tests happened to load, and a
  // file no test reached was not 0%: it was not there.
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/__tests__/**',
    '!src/**/*.{test,spec}.{ts,tsx}',
    '!src/__mocks__/**',
    '!src/e2e/**',
    '!src/jest.setup.ts',
  ],
  // Keep test infrastructure out of the coverage denominator (#328): these are
  // fixtures/mocks that support tests, not shippable product code.
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '<rootDir>/src/__tests__/fixtures/',
    '<rootDir>/src/__tests__/mocks/',
    '<rootDir>/src/__tests__/theme/helpers/',
    '<rootDir>/src/__mocks__/',
  ],
  testMatch: [
    '**/__tests__/**/*.(test|spec).[jt]s?(x)',
    '**/*.(test|spec).[jt]s?(x)',
    '!**/__tests__/helpers/**',          // Exclude ALL files in helpers
    '!**/helpers/**/*.ts',                // Exclude helper .ts files
    '!**/*.spec.ts',                     // Exclude Playwright spec files
    '!**/e2e/**',                        // Exclude all E2E directories
  ],
}

// `transformIgnorePatterns` is OR'd, and next/jest prepends its own
// `/node_modules/...` entry — so adding a custom "don't ignore X" pattern can
// never un-ignore a package on its own. Patch next's entry instead. Needed so
// `@better-auth/core` (ESM-only) can be imported by tests; see auth-ip.test.ts.
module.exports = async () => {
  const config = await createJestConfig(customJestConfig)()
  const patched = config.transformIgnorePatterns.map((pattern) =>
    pattern.startsWith('/node_modules/(?!.pnpm)')
      ? pattern.replace('(?!.pnpm)', '(?!.pnpm)(?!@better-auth/)')
      : pattern
  )
  if (patched.every((pattern, i) => pattern === config.transformIgnorePatterns[i])) {
    throw new Error(
      "next/jest's node_modules transformIgnorePatterns entry no longer matches the " +
        'expected shape, so @better-auth/core would not be transformed. Re-derive the ' +
        'patch from `npx jest --showConfig`.'
    )
  }
  config.transformIgnorePatterns = patched
  return config
}

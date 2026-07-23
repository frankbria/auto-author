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
  },
  transformIgnorePatterns: [
    // Transform better-auth and @clerk packages (they use ES modules)
    'node_modules/(?!(better-auth|@clerk/.*)/)',
  ],
  testPathIgnorePatterns: [
    '<rootDir>/src/e2e/',
    '<rootDir>/e2e/',                    // Exclude Playwright E2E tests
    '.spec.ts',                          // Exclude Playwright spec files
    'responsive.spec.ts',                // Exclude Playwright E2E specs
  ],
  // Keep test infrastructure out of the coverage denominator (#328): these are
  // fixtures/mocks that support tests, not shippable product code, and only ever
  // appeared in coverage because they get imported during the run. Excluding them
  // does not force-collect any new file (unlike collectCoverageFrom).
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '<rootDir>/src/__tests__/fixtures/',
    '<rootDir>/src/__tests__/mocks/',
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

module.exports = createJestConfig(customJestConfig)

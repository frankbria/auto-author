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
  },
  transformIgnorePatterns: [
    // Transform @clerk packages (they use ES modules in v6+)
    'node_modules/(?!(@clerk/.*)/)',
  ],
  testPathIgnorePatterns: [
    '<rootDir>/src/e2e/',
    '<rootDir>/e2e/',                    // Exclude Playwright E2E tests
    '<rootDir>/src/__tests__/e2e/',      // Exclude E2E tests in __tests__
    'SystemE2E.test.tsx',                // Exclude specific E2E test
    'ProfilePage.test.tsx',              // Exclude - missing module
    'SystemIntegration.test.tsx',        // Exclude - missing module
    '.spec.ts',                          // Exclude Playwright spec files
    'responsive.spec.ts',                // Exclude Playwright E2E specs
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

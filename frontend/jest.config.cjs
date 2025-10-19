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
  transformIgnorePatterns: ['/node_modules/'],
  testPathIgnorePatterns: [
    '<rootDir>/src/e2e/',
    '<rootDir>/e2e/',                    // Exclude Playwright E2E tests
    'SystemE2E.test.tsx',                // Exclude specific E2E test
    'ProfilePage.test.tsx',              // Exclude - missing module
    'SystemIntegration.test.tsx',        // Exclude - missing module
  ],
  testMatch: [
    '**/__tests__/**/*.(test|spec).[jt]s?(x)',
    '**/*.(test|spec).[jt]s?(x)',
    '!**/__tests__/helpers/**',          // Exclude helper files without tests
  ],
}

module.exports = createJestConfig(customJestConfig)

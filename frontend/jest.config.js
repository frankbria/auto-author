// frontend/jest.config.js
module.exports = {
  rootDir: './src',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  transform: {
    "^.+\\.(js|jsx|ts|tsx)$": "babel-jest" // 👈 critical line
  },
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
    "\\.(css|less|scss|sass)$": "identity-obj-proxy"
  },
  testPathIgnorePatterns: ['/node_modules/', '/.next/']
};

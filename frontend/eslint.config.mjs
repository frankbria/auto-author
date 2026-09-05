import nextCoreWebVitals from "eslint-config-next/core-web-vitals";

// eslint-config-next 16 ships flat config directly, so FlatCompat (and its
// undeclared `@eslint/eslintrc` import, #571) is gone. Flat config resolves
// plugin namespaces per file, so each override block below has to repeat the
// `files` glob the Next config registered those plugins under — a bare rules
// object fails with "could not find plugin".
const ALL_FILES = ["**/*.{js,jsx,mjs,ts,tsx,mts,cts}"];
const TS_FILES = ["**/*.ts", "**/*.tsx"];

const eslintConfig = [
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "coverage/**",
      "dist/**",
      "build/**",
      "out/**",
      "next-env.d.ts",
      "playwright-report/**",
      "test-results/**",
    ],
  },
  // core-web-vitals already bundles the next/typescript config, which is why
  // `@typescript-eslint/{parser,eslint-plugin}` are no longer direct devDeps.
  ...nextCoreWebVitals,
  {
    files: ALL_FILES,
    rules: {
      // Downgrade to warnings during ESLint migration
      "react/display-name": "warn",
      "react-hooks/rules-of-hooks": "warn", // Critical: needs fixing in responsiveHelpers.ts
      "react/no-unescaped-entities": "warn",
      "@next/next/no-html-link-for-pages": "warn",
      "prefer-const": "warn",
      // New in eslint-plugin-react-hooks 7, error by default and flagging 30
      // pre-existing call sites. Warned rather than fixed here to keep this an
      // ESLint upgrade instead of a React refactor — see the follow-up issue.
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/refs": "warn",
      "react-hooks/immutability": "warn",
    },
  },
  {
    files: TS_FILES,
    rules: {
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-var-requires": "warn",
      "@typescript-eslint/triple-slash-reference": "warn",
      "@typescript-eslint/no-unused-vars": "warn",
    },
  },
];

export default eslintConfig;

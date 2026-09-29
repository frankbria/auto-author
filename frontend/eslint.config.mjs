import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import { createRequire } from "node:module";

// eslint-config-next 16 ships flat config directly, so FlatCompat (and its
// undeclared `@eslint/eslintrc` import, #571) is gone. Flat config resolves
// plugin namespaces per file, so each override block below has to repeat the
// `files` glob the Next config registered those plugins under — a bare rules
// object fails with "could not find plugin".
const ALL_FILES = ["**/*.{js,jsx,mjs,ts,tsx,mts,cts}"];
const TS_FILES = ["**/*.ts", "**/*.tsx"];

// The installed react, not the range in package.json. eslint-config-next sets
// settings.react.version = "detect", the only path that calls
// context.getFilename() — removed in ESLint 10. Pinning the version skips
// detection and keeps us compatible with a future ESLint 10 bump.
const reactVersion = createRequire(import.meta.url)("react/package.json").version;

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
  { settings: { react: { version: reactVersion } } },
  {
    files: ALL_FILES,
    rules: {
      // Downgrade to warnings during ESLint migration
      "react/display-name": "warn",
      "react-hooks/rules-of-hooks": "warn", // Critical: needs fixing in responsiveHelpers.ts
      "react/no-unescaped-entities": "warn",
      "@next/next/no-html-link-for-pages": "warn",
      "prefer-const": "warn",

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

import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

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
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      // Downgrade to warnings during ESLint migration
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-var-requires": "warn",
      "@typescript-eslint/triple-slash-reference": "warn",
      "@typescript-eslint/no-unused-vars": "warn",
      "react/display-name": "warn",
      "react-hooks/rules-of-hooks": "warn", // Critical: needs fixing in responsiveHelpers.ts
      "react/no-unescaped-entities": "warn",
      "@next/next/no-html-link-for-pages": "warn",
      "prefer-const": "warn",
    },
  },
];

export default eslintConfig;

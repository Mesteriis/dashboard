import js from "@eslint/js";
import tsParser from "@typescript-eslint/parser";
import globals from "globals";
import pluginVue from "eslint-plugin-vue";

const baseRules = {
  "no-console": "error",
  "no-debugger": "error",
  "vue/multi-word-component-names": "off",
} as const;

const tsRules = {
  ...baseRules,
  "no-undef": "off",
  "no-unused-vars": "off",
} as const;

export default [
  {
    ignores: ["dist/**", "node_modules/**", "src/typed-router.d.ts"],
  },
  js.configs.recommended,
  ...pluginVue.configs["flat/essential"],
  {
    files: ["src/**/*.ts"],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        ...globals.browser,
      },
    },
    rules: tsRules,
  },
  {
    files: ["src/**/*.vue"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        parser: tsParser,
      },
      globals: {
        ...globals.browser,
      },
    },
    rules: baseRules,
  },
];

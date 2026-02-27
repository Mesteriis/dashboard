import js from "@eslint/js";
import tsParser from "@typescript-eslint/parser";
import globals from "globals";
import pluginVue from "eslint-plugin-vue";

const baseRules = {
  "no-console": "error",
  "no-debugger": "error",
  "vue/multi-word-component-names": "off",
} as const;

const noParentRelativeImports = [
  "error",
  {
    patterns: [
      {
        group: ["../*", "../../*", "../../../*", "../../../../*"],
        message:
          "Use @/ alias imports inside src instead of parent-relative paths.",
      },
    ],
  },
] as const;

const tsRules = {
  ...baseRules,
  "no-undef": "off",
  "no-unused-vars": "off",
  "no-restricted-imports": noParentRelativeImports,
} as const;

export default [
  {
    ignores: ["dist/**", "node_modules/**"],
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
  {
    files: ["src/**/*.vue"],
    rules: {
      "no-restricted-imports": noParentRelativeImports,
    },
  },
  {
    files: ["src/ui/**/*.{ts,vue}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            "../*",
            "../../*",
            "../../../*",
            "../../../../*",
            "@/components/**",
            "@/primitives/**",
            "@/views/**",
            "@/pages/**",
            "@/features/**",
            "@/app/**",
            "@/router",
          ],
        },
      ],
    },
  },
  {
    files: ["src/primitives/**/*.{ts,vue}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            "../*",
            "../../*",
            "../../../*",
            "../../../../*",
            "@/components/**",
            "@/views/**",
            "@/pages/**",
            "@/features/**",
            "@/app/**",
            "@/router",
          ],
        },
      ],
    },
  },
  {
    files: ["src/views/**/*.{ts,vue}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: ["@/pages/**", "@/app/router/**", "@/router"],
        },
      ],
    },
  },
  {
    files: ["src/pages/**/*.{ts,vue}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: ["@/ui/**", "@/primitives/**"],
        },
      ],
    },
  },
];

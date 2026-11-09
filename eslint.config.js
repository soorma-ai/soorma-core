// SPDX-License-Identifier: FSL-1.1-ALv2
// ESLint for the soorma-core workspace (NFR-WC-23; SECURITY-15).
import js from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  {
    ignores: [
      '**/node_modules/**',
      // Compiled output of the build configurations (D-CG-OI-02); git-ignored.
      '**/dist/**',
      'contract/generated/**',
      'contract/test/golden/*.ts',
      // The lint fixture holds a deliberate floating promise. The lint test
      // (tools/test/lint.test.ts) lints it explicitly; the normal run skips it.
      'tools/test/fixtures/lint/**',
    ],
  },
  js.configs.recommended,
  {
    files: ['**/*.ts'],
    extends: [...tseslint.configs.recommendedTypeChecked],
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
    },
  },
  {
    // Tests mutate untyped JSON fixtures field by field, so `any` is deliberate
    // there. The promise rules above stay on in tests.
    files: ['**/test/**/*.ts'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unsafe-member-access': 'off',
      '@typescript-eslint/no-unsafe-assignment': 'off',
    },
  },
);

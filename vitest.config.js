// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Vitest for the soorma-core workspace. Workspace packages resolve to their
// source through the `source` export condition (D-CG-OI-02), so tests need no
// build. Vitest resolves Node tests in Vite's server environment, so the
// condition goes in `ssr.resolve.conditions` (Vite 8.3.5; checked at Step 7:
// `resolve.conditions` alone does not reach it). The other entries are Vite's
// defaults for that environment, which setting the list replaces.
import { defineConfig } from 'vitest/config';

export default defineConfig({
  ssr: { resolve: { conditions: ['source', 'module', 'node', 'development|production'] } },
  test: {
    // Argon2id at 64 MiB takes about 170 ms a call (NFR-OI-11), and the flow
    // tests make dozens.
    testTimeout: 30_000,
    hookTimeout: 30_000,
    // The test-database harness (D-CG-OI-15): when TEST_DATABASE_URL is set,
    // creates the roles and a migrated template database once per run.
    // The environment store's harness (U4 D-CG-EHA-07) sets up its own template
    // on the same server.
    globalSetup: [
      'packages/org-identity/test/harness/global-setup.ts',
      'packages/env-store/test/harness/global-setup.ts',
    ],
  },
});

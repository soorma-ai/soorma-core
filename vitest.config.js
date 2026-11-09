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
});

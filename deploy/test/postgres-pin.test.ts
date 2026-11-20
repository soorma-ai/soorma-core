// SPDX-License-Identifier: FSL-1.1-ALv2
//
// One PostgreSQL across the stack and its tests (T-EHA-05 "one engine across
// the stack"; T-AR-04; D-CG-OI-10, D-CG-OI-15): the Compose file, CI's test
// database service, and `pnpm db:test` name the identical digest-pinned image.
//
// Dependabot's docker-compose update moves only the Compose file. It cannot
// update ci.yml's service image (a workflow service container) or db-test.ts's
// POSTGRES_IMAGE (a TypeScript string), so a postgres bump must edit both by
// hand; this test fails until it does.
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { POSTGRES_IMAGE } from '../local/scripts/db-test.ts';

const root = resolve(import.meta.dirname, '../..');
const COMPOSE = 'deploy/local/compose.yaml';
const CI = '.github/workflows/ci.yml';
const DB_TEST = 'deploy/local/scripts/db-test.ts';

/** Every `image: postgres…` reference in a file, anchors included. */
const postgresImages = (path: string): string[] =>
  [
    ...readFileSync(join(root, path), 'utf8').matchAll(/^\s*image:\s*['"]?(postgres:[^\s'"]+)/gm),
  ].map((m) => m[1]!);

const PINNED = /^postgres:[^@\s]+@sha256:[0-9a-f]{64}$/;

describe('the PostgreSQL pin: one image for the stack, CI, and db:test', () => {
  const compose = postgresImages(COMPOSE);
  const ci = postgresImages(CI);

  it('the Compose file names one digest-pinned postgres image', () => {
    expect(compose.length, COMPOSE).toBeGreaterThan(0);
    expect([...new Set(compose)], COMPOSE).toHaveLength(1);
    expect(compose[0], COMPOSE).toMatch(PINNED);
  });

  it("ci.yml's service and db-test.ts name the identical image", () => {
    expect(ci.length, CI).toBeGreaterThan(0);
    const reference = compose[0];
    const found: [string, string[]][] = [
      [CI, ci],
      [DB_TEST, [POSTGRES_IMAGE]],
    ];
    const differ = found
      .filter(([, images]) => images.some((image) => image !== reference))
      .map(([path, images]) => `${path} has ${[...new Set(images)].join(', ')}`);
    expect(
      differ,
      `postgres pins differ from ${COMPOSE} (${reference}): ${differ.join('; ')}. ` +
        `Dependabot updates only ${COMPOSE}; it cannot update ${CI}'s service image ` +
        `or ${DB_TEST}'s POSTGRES_IMAGE, so a postgres bump edits both to match`,
    ).toEqual([]);
  });
});

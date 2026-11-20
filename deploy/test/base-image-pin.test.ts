// SPDX-License-Identifier: FSL-1.1-ALv2
//
// One build image and one runtime image for the four service images
// (D-CG-OI-10; NFR-OI-26): S1 to S4's Dockerfiles name the identical
// digest-pinned `node` build stage and distroless runtime stage.
//
// Dependabot's docker entry covers all four directories and groups updates by
// dependency name (.github/dependabot.yml): a node bump is one pull request
// across all four Dockerfiles, and a distroless bump another. This test fails
// if a bump, or a hand edit, moves some Dockerfiles and not the others.
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const root = resolve(import.meta.dirname, '../..');
const DOCKERFILES = [
  'services/org-gateway/Dockerfile',
  'services/control-gateway/Dockerfile',
  'services/data-gateway/Dockerfile',
  'services/event-ingest/Dockerfile',
] as const;

const PINNED = /^[^\s@]+:[^\s@]+@sha256:[0-9a-f]{64}$/;

/** A Dockerfile's FROM images, in order, without any `AS name`. */
const fromImages = (path: string): string[] =>
  [...readFileSync(join(root, path), 'utf8').matchAll(/^FROM\s+(\S+)/gm)].map((m) => m[1]!);

const stages = DOCKERFILES.map((path) => {
  const images = fromImages(path);
  return { path, images, build: images[0], runtime: images.at(-1) };
});

/** The stage's distinct images, each with the files naming it. */
const byImage = (stage: 'build' | 'runtime'): string[] => {
  const files = new Map<string, string[]>();
  for (const s of stages)
    files.set(s[stage] ?? '(none)', [...(files.get(s[stage] ?? '(none)') ?? []), s.path]);
  return [...files].map(([image, paths]) => `${image} in ${paths.join(', ')}`);
};

describe('the service base images: one build pin and one runtime pin across S1 to S4', () => {
  it('each Dockerfile has a node build stage and a distroless runtime stage, digest-pinned', () => {
    for (const s of stages) {
      expect(s.images, s.path).toHaveLength(2);
      expect(s.build, s.path).toMatch(/^node:/);
      expect(s.runtime, s.path).toMatch(/^gcr\.io\/distroless\/nodejs\d+-debian\d+:nonroot@/);
      for (const image of s.images) expect(image, s.path).toMatch(PINNED);
    }
  });

  for (const stage of ['build', 'runtime'] as const)
    it(`the four Dockerfiles name one ${stage} image`, () => {
      const found = byImage(stage);
      expect(
        found,
        `the ${stage} stage differs across the service Dockerfiles: ${found.join('; ')}. ` +
          'All four share one pin; a base-image bump edits every Dockerfile to match',
      ).toHaveLength(1);
    });
});

// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-AC-069's docs half (U6 Infrastructure Design §11; D-ID-AC-17): S3's
// README keeps its Operations notes, and its rotation steps say "wait at least
// 15 minutes" at step 3, tied to the agent credential's lifetime, so the note
// cannot drift silently from the constant. The fixed values it names equal
// the constants.
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  AGENT_CREDENTIAL_LIFETIME_MS,
  LINEAGE_MAX_AGE_MS,
  PROPAGATION_BOUND_MS,
} from '../../packages/credentials/src/lifetimes.ts';

const readme = readFileSync(
  join(resolve(import.meta.dirname, '../..'), 'services/data-gateway/README.md'),
  'utf8',
);

/** The text of a `###` section, up to the next heading of level 2 or 3. */
function section(heading: string): string {
  const lines = readme.split('\n');
  const start = lines.findIndex((l) => l.trim() === `### ${heading}`);
  expect(start, heading).toBeGreaterThanOrEqual(0);
  const end = lines.findIndex((l, i) => i > start && /^#{2,3} /.test(l));
  return lines
    .slice(start + 1, end < 0 ? undefined : end)
    .join('\n')
    .replace(/\s+/g, ' ');
}

const minutes = AGENT_CREDENTIAL_LIFETIME_MS / 60_000;

describe('TC-AC-069: S3’s README says wait at least 15 minutes in its rotation steps', () => {
  it('has the Operations section and each of its notes', () => {
    expect(readme).toMatch(/^## Operations$/m);
    for (const heading of [
      "Rotating E's agent key",
      "The bound's counter secret",
      'The lockout residual',
      'When the store is down',
      'When the organization level is down',
      'The fixed values',
      'Upgrading a local stack to U6',
    ])
      expect(section(heading).length, heading).toBeGreaterThan(0);
  });

  it('the rotation has three steps; the third waits at least the credential lifetime', () => {
    const text = section("Rotating E's agent key");
    const steps = text.split(/ (?=\d\. )/).filter((s) => /^\d\. /.test(s));
    expect(steps).toHaveLength(3);
    expect(steps[2]).toContain(`Wait at least ${minutes} minutes after step 2`);
    expect(steps[0]).toContain('keys.verify');
    expect(steps[1]).toContain('keys.signing');
  });

  it('names the fixed values as the constants are', () => {
    const text = section('The fixed values');
    expect(text).toContain(`(${PROPAGATION_BOUND_MS / 1000} seconds)`);
    expect(text).toContain(`(${minutes} minutes)`);
    expect(text).toContain(`(${LINEAGE_MAX_AGE_MS / 3_600_000} hours)`);
    expect(text).toContain('not configuration');
  });

  it('the lockout, the store, S1, and the upgrade say what they must', () => {
    expect(section('The lockout residual')).toContain('at most 60 seconds');
    expect(section('The lockout residual')).toContain('Running instances renew unaffected');
    expect(section('When the store is down')).toContain('`Retry-After: 5`');
    expect(section('When the organization level is down')).toContain('no dependency on S1');
    expect(section('Upgrading a local stack to U6')).toContain('pnpm stack:down -v');
  });
});

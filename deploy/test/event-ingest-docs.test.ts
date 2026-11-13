// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-ET-087 (U7 Infrastructure Design §12; D-ID-ET-13, 18): S4's README keeps
// its Operations notes. The seal rotation has three steps and its third says
// "wait at least 24 hours" (the lineage's maximum age), with the consequence
// of removing the old key; the verify-key step is tied to S3's; and the fixed
// values it names equal the constants, so the notes cannot drift silently.
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  AGENT_CREDENTIAL_LIFETIME_MS,
  LINEAGE_MAX_AGE_MS,
  PROPAGATION_BOUND_MS,
} from '../../packages/credentials/src/lifetimes.ts';
import * as settings from '../../services/event-ingest/src/settings.ts';

const readme = readFileSync(
  join(resolve(import.meta.dirname, '../..'), 'services/event-ingest/README.md'),
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

const KiB = (n: number): string => `${n / 1024} KiB`;

describe('TC-ET-087: S4’s README Operations match the code', () => {
  it('has the Operations section and each of its notes', () => {
    expect(readme).toMatch(/^## Operations$/m);
    for (const heading of [
      "Rotating E's seal key",
      "Rotating E's agent verify key",
      'When the store is down',
      'When the organization level is down',
      'One S4 per environment',
      'The fixed values',
      'Upgrading a local stack to U7',
    ])
      expect(section(heading).length, heading).toBeGreaterThan(0);
  });

  it('the seal rotation: three steps, the third waits at least 24 hours, and the consequence', () => {
    const text = section("Rotating E's seal key");
    const steps = text.split(/ (?=\d\. )/).filter((s) => /^\d\. /.test(s));
    expect(steps).toHaveLength(3);
    expect(steps[0]).toContain('sealKeys.keys');
    expect(steps[0]).toContain('it verifies with both, and still seals with the old');
    expect(steps[1]).toContain('sealKeys.current');
    expect(steps[2]).toContain(
      `Wait at least ${LINEAGE_MAX_AGE_MS / 3_600_000} hours after step 2`,
    );
    expect(text).toContain(
      "Once the old key is removed, envelopes sealed with it can't be forwarded",
    );
    expect(text).toContain('`invalid_inbound_context`');
  });

  it('the verify-key step follows S3’s, waiting its credential lifetime', () => {
    const text = section("Rotating E's agent verify key");
    expect(text).toContain('eventIngest.keys.agentVerify');
    expect(text).toContain(`wait at least ${AGENT_CREDENTIAL_LIFETIME_MS / 60_000} minutes`);
  });

  it('names the fixed values as the constants are', () => {
    const text = section('The fixed values');
    expect(text).toContain(`(${PROPAGATION_BOUND_MS / 1000} seconds) is \`PROPAGATION_BOUND_MS\``);
    expect(text).toContain('not configuration');
    expect(text).toContain(`Delivery payload bound (${KiB(settings.DELIVERY_PAYLOAD_BOUND)}`);
    expect(text).toContain(
      `publish ${KiB(settings.PUBLISH_BODY_LIMIT)}, subscribe ${KiB(settings.SUBSCRIBE_BODY_LIMIT)}`,
    );
    expect(text).toContain(`at most ${settings.MAX_STREAMS} open streams`);
    expect(text).toContain(`a ${settings.SEND_BUFFER_BYTES / 1_048_576} MiB send buffer`);
    expect(text).toContain(`after ${settings.HEARTBEAT_MS / 1000} seconds of silence`);
    expect(settings.SWEEP_INTERVAL_MS).toBe(1000);
    expect(text).toContain('a revocation sweep every second');
    expect(text).toContain(`at most ${settings.REQUEST_PERMITS} requests in flight`);
    expect(text).toContain(`\`Retry-After: ${settings.RETRY_AFTER_SECONDS}\``);
  });

  it('the store, S1, one S4, and the upgrade say what they must', () => {
    expect(section('When the store is down')).toContain('`Retry-After: 5`');
    expect(section('When the store is down')).toContain('GAP-ET-001');
    expect(section('When the organization level is down')).toContain('no dependency on S1');
    expect(section('One S4 per environment')).toContain('exactly one S4 per environment');
    expect(section('Upgrading a local stack to U7')).toContain('pnpm stack:down -v');
    expect(readme).toContain('Its memory limit is `512m`');
  });
});

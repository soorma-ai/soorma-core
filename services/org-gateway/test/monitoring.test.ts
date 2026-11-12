// SPDX-License-Identifier: FSL-1.1-ALv2
// The monitoring files (NFR-OI-23; SECURITY-14, files only, the user's
// decision): TC-OI-049's monitoring half.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { Ajv2020 } from 'ajv/dist/2020.js';
import { describe, expect, it } from 'vitest';
import { parse } from 'yaml';
import { SECURITY_EVENTS } from '../src/security-log.ts';
import { SECURITY_EVENTS as S2_EVENTS } from '../../control-gateway/src/security-log.ts';
import { SECURITY_EVENTS as S3_EVENTS } from '../../data-gateway/src/security-log.ts';

const root = resolve(import.meta.dirname, '../../..');
const dir = join(root, 'deploy/monitoring');
const load = (name: string): unknown => parse(readFileSync(join(dir, name), 'utf8')) as unknown;
const schema = (name: string): object =>
  JSON.parse(readFileSync(join(dir, name), 'utf8')) as object;

interface Alerts {
  events: string[];
  rules: { id: string; event: string; groupBy: string; threshold: { count: number } }[];
}
interface Dashboard {
  panels: { events: string[]; groupBy?: string }[];
}

const alerts = load('alerts.yaml') as Alerts;
const dashboard = load('dashboard.yaml') as Dashboard;

function sourceFiles(base: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(base)) {
    const full = join(base, name);
    if (statSync(full).isDirectory()) out.push(...sourceFiles(full));
    else if (name.endsWith('.ts')) out.push(full);
  }
  return out;
}

describe('the monitoring files', () => {
  it('validate against their schemas', () => {
    const ajv = new Ajv2020({ strict: true, allErrors: true });
    expect(ajv.validate(schema('alerts.schema.json'), alerts), ajv.errorsText()).toBe(true);
    expect(ajv.validate(schema('dashboard.schema.json'), dashboard), ajv.errorsText()).toBe(true);
  });

  // The whole-file checks (the events list against every service's, and every
  // rule and panel against that list) are deploy/test/monitoring.test.ts's
  // (U4 D-CG-EHA-17; TC-EHA-087).
  it("list every one of S1's events", () => {
    for (const event of SECURITY_EVENTS) expect(alerts.events).toContain(event);
  });

  it('carry the rules NFR-OI-23 names, grouping humans by pseudonym, never by identifier', () => {
    const rule = (event: string) => alerts.rules.find((r) => r.event === event);
    expect(rule('auth.failed')).toMatchObject({ groupBy: 'pseudonym' });
    for (const event of ['auth.bound_refused', 'internal.call_refused', 'failed_attempt.dropped'])
      expect(rule(event)?.threshold.count).toBe(1);
    // U6 (the user's decision): a logical agent is not a human, so only a rule
    // for an event S3 alone emits may be grouped by agent.
    const s3Only = (event: string): boolean =>
      (S3_EVENTS as readonly string[]).includes(event) &&
      !(SECURITY_EVENTS as readonly string[]).includes(event) &&
      !(S2_EVENTS as readonly string[]).includes(event);
    const groupings = [
      ...alerts.rules
        .filter((r) => !(r.groupBy === 'agent' && s3Only(r.event)))
        .map((r) => r.groupBy),
      ...dashboard.panels.map((p) => p.groupBy),
    ];
    expect(
      groupings.every(
        (g) => g === undefined || ['none', 'pseudonym', 'environment', 'code'].includes(g),
      ),
    ).toBe(true);
  });

  it('every listed event is emitted somewhere in the service', () => {
    const source = sourceFiles(join(root, 'services/org-gateway/src'))
      .map((f) => readFileSync(f, 'utf8'))
      .join('\n');
    for (const event of SECURITY_EVENTS) expect(source, event).toContain(`'${event}'`);
    const emitted = [...source.matchAll(/\.event\(\s*'([a-z_.]+)'/g)].map((m) => m[1]);
    for (const event of SECURITY_EVENTS) expect(emitted, event).toContain(event);
  });
});

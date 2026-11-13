// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-ET-069 (U7 NP-ET-16; Infrastructure Design §13): S4's events and alert
// rules. alerts.yaml lists every S4 event once; S4's overlap with S1 to S3 is
// exactly store.unavailable and throttle.refused (pinned also in U4's
// monitoring.test.ts); S4's four rules carry their thresholds, grouped by
// environment or code, never by agent or a human; every S4 event is emitted
// in S4's source. Nothing evaluates them in M1 (SECURITY-14).
import { readdirSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { Ajv2020 } from 'ajv/dist/2020.js';
import { describe, expect, it } from 'vitest';
import { parse } from 'yaml';
import { SECURITY_EVENTS as S1_EVENTS } from '../../services/org-gateway/src/security-log.ts';
import { SECURITY_EVENTS as S2_EVENTS } from '../../services/control-gateway/src/security-log.ts';
import { SECURITY_EVENTS as S3_EVENTS } from '../../services/data-gateway/src/security-log.ts';
import { SECURITY_EVENTS as S4_EVENTS } from '../../services/event-ingest/src/security-log.ts';

const root = resolve(import.meta.dirname, '../..');
const dir = join(root, 'deploy/monitoring');

interface Rule {
  id: string;
  event: string;
  groupBy: string;
  codes?: string[];
  threshold: { count: number; windowMinutes: number };
  severity: string;
}
const alerts = parse(readFileSync(join(dir, 'alerts.yaml'), 'utf8')) as {
  events: string[];
  rules: Rule[];
};
const schema = JSON.parse(readFileSync(join(dir, 'alerts.schema.json'), 'utf8')) as object;
const rule = (id: string): Rule | undefined => alerts.rules.find((r) => r.id === id);

const S4_RULES = [
  'stream-revoked',
  'stream-overflow',
  'ingest-refused-burst',
  'envelope-refused-burst',
];

describe('TC-ET-069: S4’s events and alert rules, the overlap pinned', () => {
  it('the file validates; every S4 event is listed exactly once', () => {
    const ajv = new Ajv2020({ strict: true, allErrors: true });
    expect(ajv.validate(schema, alerts), ajv.errorsText()).toBe(true);
    for (const event of S4_EVENTS)
      expect(
        alerts.events.filter((e) => e === event),
        event,
      ).toHaveLength(1);
  });

  it('S4’s overlap with S1 to S3 is exactly store.unavailable and throttle.refused', () => {
    const others = new Set<string>([...S1_EVENTS, ...S2_EVENTS, ...S3_EVENTS]);
    expect(S4_EVENTS.filter((e) => others.has(e)).sort()).toEqual([
      'store.unavailable',
      'throttle.refused',
    ]);
  });

  it('S4’s four rules carry their thresholds, by environment or code, never by agent', () => {
    expect(rule('stream-revoked')).toMatchObject({
      event: 'stream.revoked',
      groupBy: 'environment',
      threshold: { count: 1, windowMinutes: 15 },
    });
    expect(rule('stream-overflow')).toMatchObject({
      event: 'stream.overflow',
      groupBy: 'environment',
      threshold: { count: 5, windowMinutes: 5 },
    });
    for (const [id, event] of [
      ['ingest-refused-burst', 'ingest.refused'],
      ['envelope-refused-burst', 'envelope.refused'],
    ] as const)
      expect(rule(id)).toMatchObject({
        event,
        groupBy: 'code',
        threshold: { count: 20, windowMinutes: 5 },
      });
    for (const id of S4_RULES) {
      expect(S4_EVENTS, id).toContain(rule(id)?.event);
      expect(['environment', 'code'], id).toContain(rule(id)?.groupBy);
    }
    // The shared rules are U4's, unchanged.
    expect(rule('env-store-unavailable')?.event).toBe('store.unavailable');
    expect(rule('throttle-refused')?.event).toBe('throttle.refused');
  });

  it('every S4 event is emitted in S4’s source', () => {
    const src = join(root, 'services/event-ingest/src');
    const source = readdirSync(src, { recursive: true, encoding: 'utf8' })
      .filter((f) => f.endsWith('.ts') && !f.endsWith('security-log.ts'))
      .map((f) => readFileSync(join(src, f), 'utf8'))
      .join('\n')
      // The security log's own port emits envelope.refused for U3's admit.
      .concat(readFileSync(join(src, 'security-log.ts'), 'utf8').split('SECURITY_EVENTS')[2] ?? '');
    for (const event of S4_EVENTS) expect(source, event).toContain(`'${event}'`);
  });
});

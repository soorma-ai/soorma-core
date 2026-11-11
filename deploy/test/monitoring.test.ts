// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The monitoring files as a whole (TC-EHA-087; U4 Infrastructure Design §9;
// D-CG-EHA-17): both validate against their schemas; `events` is exactly the
// union of every service's security events (S1's and S2's); every rule and
// panel names one of them; U4's five rules carry §9's thresholds; and each S2
// event has a panel grouped by environment. Nothing evaluates them in M1
// (SECURITY-14, the user's decision).
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { Ajv2020 } from 'ajv/dist/2020.js';
import { describe, expect, it } from 'vitest';
import { parse } from 'yaml';
import { SECURITY_EVENTS as S1_EVENTS } from '../../services/org-gateway/src/security-log.ts';
import { SECURITY_EVENTS as S2_EVENTS } from '../../services/control-gateway/src/security-log.ts';

const dir = resolve(import.meta.dirname, '../monitoring');
const load = (name: string): unknown => parse(readFileSync(join(dir, name), 'utf8')) as unknown;
const schema = (name: string): object =>
  JSON.parse(readFileSync(join(dir, name), 'utf8')) as object;

interface Alerts {
  events: string[];
  rules: {
    id: string;
    event: string;
    groupBy: string;
    threshold: { count: number; windowMinutes: number };
    severity: string;
  }[];
}
interface Dashboard {
  panels: { events: string[]; groupBy?: string }[];
}

const alerts = load('alerts.yaml') as Alerts;
const dashboard = load('dashboard.yaml') as Dashboard;
const union: string[] = [...S1_EVENTS, ...S2_EVENTS];

describe('TC-EHA-087: the monitoring files validate, and name only defined events', () => {
  it('validate against their schemas', () => {
    const ajv = new Ajv2020({ strict: true, allErrors: true });
    expect(ajv.validate(schema('alerts.schema.json'), alerts), ajv.errorsText()).toBe(true);
    expect(ajv.validate(schema('dashboard.schema.json'), dashboard), ajv.errorsText()).toBe(true);
  });

  it("list exactly the union of S1's and S2's events, each once", () => {
    expect(new Set(union).size).toBe(union.length);
    expect(new Set(alerts.events).size).toBe(alerts.events.length);
    expect([...alerts.events].sort()).toEqual([...union].sort());
  });

  it('name only listed events, in every rule and panel', () => {
    for (const rule of alerts.rules) expect(union, rule.id).toContain(rule.event);
    for (const panel of dashboard.panels)
      for (const event of panel.events) expect(union).toContain(event);
  });

  it("carry U4's five rules with §9's thresholds", () => {
    const rule = (id: string) => alerts.rules.find((r) => r.id === id);
    expect(rule('credential-refused-repeated')).toMatchObject({
      event: 'credential.refused',
      groupBy: 'pseudonym',
      threshold: { count: 5, windowMinutes: 15 },
      severity: 'warning',
    });
    expect(rule('grant-denied')).toMatchObject({
      event: 'grant.denied',
      groupBy: 'pseudonym',
      threshold: { count: 1, windowMinutes: 15 },
      severity: 'warning',
    });
    expect(rule('orglevel-unavailable')).toMatchObject({
      event: 'orglevel.unavailable',
      groupBy: 'environment',
      threshold: { count: 1, windowMinutes: 5 },
      severity: 'critical',
    });
    expect(rule('env-store-unavailable')).toMatchObject({
      event: 'store.unavailable',
      groupBy: 'environment',
      threshold: { count: 1, windowMinutes: 5 },
      severity: 'critical',
    });
    expect(rule('throttle-refused')).toMatchObject({
      event: 'throttle.refused',
      groupBy: 'environment',
      threshold: { count: 1, windowMinutes: 5 },
      severity: 'warning',
    });
    expect(new Set(alerts.rules.map((r) => r.id)).size).toBe(alerts.rules.length);
  });

  it('give each S2 event a panel, grouped by environment', () => {
    for (const event of S2_EVENTS)
      expect(
        dashboard.panels.some((p) => p.events.includes(event) && p.groupBy === 'environment'),
        event,
      ).toBe(true);
  });
});

// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-AC-073 (NFR-AC-23; the user's decision on S3's alert rules): S3's four
// rules are present and valid. The revoked-credential rules count only the
// revocation reasons (`codes`), so they never fire on an expiry, a record
// mismatch, or any other refusal. The two additions to U2's format
// (`groupBy: agent`, an optional `codes` list) leave every earlier rule as it
// was: none of them carries `codes`. Nothing evaluates the rules in M1
// (SECURITY-14).
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { Ajv2020 } from 'ajv/dist/2020.js';
import { describe, expect, it } from 'vitest';
import { parse } from 'yaml';
import { SECURITY_EVENTS as S3_EVENTS } from '../../services/data-gateway/src/security-log.ts';

const dir = resolve(import.meta.dirname, '../monitoring');

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

const S3_RULES = [
  'bootstrap-refused-repeated',
  'revoked-credential-renewal',
  'revoked-agent-bootstrap',
  'bound-refused',
];

describe('TC-AC-073: S3’s alert rules validate', () => {
  it('the file validates against the schema, which accepts groupBy agent and codes', () => {
    const ajv = new Ajv2020({ strict: true, allErrors: true });
    expect(ajv.validate(schema, alerts), ajv.errorsText()).toBe(true);
  });

  it('S3’s four rules, grouped by agent, with U4’s thresholds', () => {
    expect(rule('bootstrap-refused-repeated')).toEqual({
      id: 'bootstrap-refused-repeated',
      event: 'bootstrap.refused',
      groupBy: 'agent',
      threshold: { count: 5, windowMinutes: 15 },
      severity: 'warning',
      description: expect.any(String) as unknown,
    });
    expect(rule('revoked-credential-renewal')).toMatchObject({
      event: 'renewal.refused',
      groupBy: 'agent',
      threshold: { count: 1, windowMinutes: 15 },
    });
    expect(rule('revoked-agent-bootstrap')).toMatchObject({
      event: 'bootstrap.refused',
      groupBy: 'agent',
      threshold: { count: 1, windowMinutes: 15 },
    });
    expect(rule('bound-refused')).toMatchObject({
      event: 'bound.refused',
      groupBy: 'agent',
      threshold: { count: 1, windowMinutes: 15 },
    });
    for (const id of S3_RULES) expect(S3_EVENTS, id).toContain(rule(id)?.event);
  });

  it('the revoked-credential rules count only the revocation reasons', () => {
    expect([...(rule('revoked-credential-renewal')?.codes ?? [])].sort()).toEqual([
      'agent_revoked',
      'credential_revoked',
    ]);
    expect(rule('revoked-agent-bootstrap')?.codes).toEqual(['agent_revoked']);
    for (const id of ['revoked-credential-renewal', 'revoked-agent-bootstrap'])
      for (const other of ['expired', 'record_mismatch', 'no_record', 'secret_mismatch'])
        expect(rule(id)?.codes, `${id} ${other}`).not.toContain(other);
  });

  it('only those two rules carry codes: every earlier rule counts every occurrence, as before', () => {
    expect(
      alerts.rules
        .filter((r) => r.codes !== undefined)
        .map((r) => r.id)
        .sort(),
    ).toEqual(['revoked-agent-bootstrap', 'revoked-credential-renewal']);
  });

  it('the header comment defines groupBy agent and codes', () => {
    const header = readFileSync(join(dir, 'alerts.yaml'), 'utf8').split('\nversion:')[0]!;
    expect(header).toContain('`groupBy: agent`');
    expect(header).toContain('`codes`');
    expect(header).toContain('counts every');
  });
});

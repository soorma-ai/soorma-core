// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-AC-038 (NFR-AC-05; NP-AC-01): the contract publishes B as the platform's
// bound and L and M as upper bounds only, with the three client rules, and the
// published values equal the code's constants. A changed constant without the
// contract's text (or the reverse) fails here.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  AGENT_CREDENTIAL_LIFETIME_MS,
  LINEAGE_MAX_AGE_MS,
  PROPAGATION_BOUND_MS,
} from '../src/lifetimes.ts';

const CREDENTIALS_MD = join(import.meta.dirname, '../../../contract/conventions/credentials.md');

/** The *Revocation and Lifetimes* section, emphasis removed and whitespace collapsed. */
function section(): string {
  const text = readFileSync(CREDENTIALS_MD, 'utf8');
  const start = text.indexOf('## Revocation and Lifetimes');
  expect(start, 'the section exists').toBeGreaterThanOrEqual(0);
  const end = text.indexOf('\n## ', start + 1);
  return text
    .slice(start, end === -1 ? undefined : end)
    .replace(/\*\*/g, '')
    .replace(/\s+/g, ' ');
}

describe('TC-AC-038: the contract publishes B, L, and M from the code constants', () => {
  it('B is published as the platform bound, in seconds, equal to PROPAGATION_BOUND_MS', () => {
    const s = section();
    expect(s).toContain(
      `Revocation reaches every request within ${PROPAGATION_BOUND_MS / 1000} seconds.`,
    );
    expect(s).toContain("the platform's propagation bound");
    expect(s).toContain('not configurable per tenant');
    expect(s).toContain('denies the request with `unavailable`');
  });

  it('L and M are published as upper bounds only, equal to the constants', () => {
    const s = section();
    expect(s).toContain(
      `valid for at most ${AGENT_CREDENTIAL_LIFETIME_MS / 60_000} minutes from its bootstrap or its latest renewal`,
    );
    expect(s).toContain(
      `renewal never extends it past ${LINEAGE_MAX_AGE_MS / 3_600_000} hours from its bootstrap`,
    );
    expect(s).toContain('Both are upper bounds only');
  });

  it('states the three client rules', () => {
    const s = section();
    expect(s).toContain("Schedules renewal from the response's `expiresAt`");
    expect(s).toContain('Bootstraps again when renewal answers `credential_expired`');
    expect(s).toContain('Never hard-codes either lifetime');
  });
});

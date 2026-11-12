// SPDX-License-Identifier: FSL-1.1-ALv2
// P1's agent checks (U6 D-AC-10, 27; NP-AC-11): TC-AC-085 (checkAgentRequest by
// callbacks, each outcome; P1 still depends on service-kit only), TC-AC-039
// and TC-AC-012 (P1's half: every presenter row of ID §8b at S3, refused by
// kind without verifying).
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { UnavailableError, type SecretText } from '@soorma/service-kit';
import { describe, expect, it } from 'vitest';
import {
  checkAgentRequest,
  presentedAgentCredential,
  type AgentRequestChecks,
  type CheckedAgentContext,
} from '../src/index.ts';

const context: CheckedAgentContext = {
  scope: { organization: 'o1', project: 'p1', environment: 'e' },
  agent: 'a',
  instance: 'i-1',
  cid: 'c1',
};
const AC = 'soorma_ac_aaaa.bbbb.cccc';
const headers = (...pairs: [string, string][]) => pairs.flat();

function checks(over: Partial<AgentRequestChecks> = {}) {
  const seen: { verified: SecretText[]; revocation: number } = { verified: [], revocation: 0 };
  const c: AgentRequestChecks = {
    verify: (t) => {
      seen.verified.push(t);
      return Promise.resolve({ ok: true, context });
    },
    revocation: () => {
      seen.revocation++;
      return Promise.resolve('not_revoked');
    },
    ...over,
  };
  return { c, seen };
}

describe('TC-AC-085: checkAgentRequest runs the presenter, then verify, then O3, by callbacks', () => {
  it('accepted: the Checked Agent Context', async () => {
    const { c, seen } = checks();
    expect(await checkAgentRequest(headers(['Authorization', `Bearer ${AC}`]), c)).toEqual({
      accepted: true,
      context,
    });
    expect(seen.verified).toEqual([AC]);
    expect(seen.revocation).toBe(1);
  });

  it('a verification refusal or expiry is passed through, and O3 is not read', async () => {
    for (const code of ['credential_refused', 'credential_expired'] as const) {
      const { c, seen } = checks({
        verify: () => Promise.resolve({ ok: false, code, reason: 'x' }),
      });
      expect(await checkAgentRequest(headers(['Authorization', `Bearer ${AC}`]), c)).toEqual({
        accepted: false,
        code,
        reason: 'x',
      });
      expect(seen.revocation).toBe(0);
    }
  });

  it('revoked is credential_refused; an O3 read that cannot answer throws (unavailable)', async () => {
    const revoked = checks({ revocation: () => Promise.resolve('revoked') });
    expect(await checkAgentRequest(headers(['Authorization', `Bearer ${AC}`]), revoked.c)).toEqual({
      accepted: false,
      code: 'credential_refused',
      reason: 'credential_revoked',
    });
    const down = checks({
      revocation: () => Promise.reject(new UnavailableError('down', 5)),
    });
    await expect(
      checkAgentRequest(headers(['Authorization', `Bearer ${AC}`]), down.c),
    ).rejects.toBeInstanceOf(UnavailableError);
  });

  it('P1 still depends on @soorma/service-kit only (no P5)', () => {
    const manifest = JSON.parse(
      readFileSync(join(import.meta.dirname, '../package.json'), 'utf8'),
    ) as { dependencies: Record<string, string> };
    expect(Object.keys(manifest.dependencies)).toEqual(['@soorma/service-kit']);
  });
});

describe('TC-AC-039, TC-AC-012 (P1’s half): every other presenter is refused by kind, without verifying', () => {
  const rows: [string, string[]][] = [
    [
      'a human environment credential',
      headers(['Authorization', 'Bearer soorma_ec_aaaa.bbbb.cccc']),
    ],
    ['an organization sign-in', headers(['Authorization', 'Bearer soorma_si_aaaa.bbbb.cccc'])],
    ['a delegation credential', headers(['Authorization', 'Bearer soorma_dc_aaaa.bbbb.cccc'])],
    ['an unknown prefix', headers(['Authorization', 'Bearer something_else'])],
    ['no credential', []],
    [
      'two credentials',
      headers(['Authorization', `Bearer ${AC}`], ['Authorization', `Bearer ${AC}`]),
    ],
    [
      'an agent credential beside Soorma-Delegation',
      headers(['Authorization', `Bearer ${AC}`], ['Soorma-Delegation', 'soorma_dc_x']),
    ],
    ['not a bearer', headers(['Authorization', `Basic ${AC}`])],
  ];
  it.each(rows)('%s: credential_refused, and verify never called', async (_name, raw) => {
    const { c, seen } = checks();
    expect(await checkAgentRequest(raw, c)).toEqual({
      accepted: false,
      code: 'credential_refused',
      reason: 'presenter',
    });
    expect(seen.verified).toEqual([]);
    expect(presentedAgentCredential(raw)).toBeUndefined();
  });
});

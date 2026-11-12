// SPDX-License-Identifier: FSL-1.1-ALv2
// TC-AC-084: the secret check finds U6's two values, shaped like the real
// thing, and never an obviously fake one (NP-AC-12, with the user's
// condition: fixtures use fake values; no exception in the check). U2's
// patterns and their tests (code-checks.test.ts) are unchanged.
import { randomBytes } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { FIXTURE_PATHS, SECRET_PATTERNS, textFindings } from '../checks/secrets.ts';

const b64 = (bytes: number): string => randomBytes(bytes).toString('base64url');

describe('TC-AC-084: agent credentials and registration secrets are found', () => {
  it('an agent credential shaped like a real token is found', () => {
    const token = `soorma_ac_${b64(30)}.${b64(120)}.${b64(64)}`;
    expect(textFindings('f', `Authorization: Bearer ${token}`)).toEqual([
      { check: 'secrets', location: 'f', message: 'holds an agent credential' },
    ]);
  });

  it('a registration secret in its exact shape is found', () => {
    const secret = `soorma_rs_${b64(16)}.${b64(32)}`;
    expect(textFindings('f', `{"secret":"${secret}"}`)).toEqual([
      { check: 'secrets', location: 'f', message: 'holds a registration secret' },
    ]);
  });

  it('obviously fake values are not matched', () => {
    expect(
      textFindings(
        'f',
        "const t = 'soorma_ac_x'; const s = 'soorma_rs_x.y'; const u = 'soorma_ac_abc.def.ghi';",
      ),
    ).toEqual([]);
  });

  it('a registration secret with a part of the wrong length is not matched', () => {
    expect(textFindings('f', `soorma_rs_${'a'.repeat(21)}.${'b'.repeat(43)}`)).toEqual([]);
  });

  it("U2's patterns are still there, and no fixture path was added", () => {
    expect(SECRET_PATTERNS.map((p) => p.name)).toEqual([
      'enrollment material',
      'a sign-in token',
      'a private key',
      'an agent credential',
      'a registration secret',
    ]);
    expect(FIXTURE_PATHS.map(String)).toEqual([String(/^contract\/fixtures\//)]);
  });
});

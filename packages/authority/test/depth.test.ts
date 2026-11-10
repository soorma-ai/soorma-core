// SPDX-License-Identifier: FSL-1.1-ALv2
// TC-AE-037 step 1: maximum depth, from a fixed 1 MiB raw body (NP-07;
// NFR-AE-19). The body's inbound.envelope holds an unknown field nested as
// deeply as fits. It is parsed with JSON.parse, as S4 parses, and run through
// admit: the outcome is invalid_inbound_context, never a crash, a RangeError,
// or a stack overflow. 1 MiB stays valid whatever step-1 limit U7 sets, as
// long as that limit is at most 1 MiB; U7's own edge test uses its limit.
import { describe, expect, it } from 'vitest';
import { admissionE, envelope, request, TRACEPARENT } from './support.ts';

const MIB = 1024 * 1024;

function rawBody(): string {
  const head = JSON.stringify(envelope(['a'])).slice(0, -1); // the envelope, open
  const prefix = `{"clientContractVersion":"0.1.0","traceContext":{"traceparent":"${TRACEPARENT}"},"inbound":{"envelope":${head},"x-deep":`;
  const suffix = `},"seal":"v1.k1.${'A'.repeat(43)}"}}`;
  const depth = Math.floor((MIB - prefix.length - suffix.length - 1) / 2);
  const body = `${prefix}${'['.repeat(depth)}0${']'.repeat(depth)}${suffix}`;
  return body + ' '.repeat(MIB - body.length);
}

describe('TC-AE-037 step 1: a 1 MiB raw body nested as deeply as fits', () => {
  it('is refused invalid_inbound_context, with no crash', async () => {
    const raw = rawBody();
    expect(Buffer.byteLength(raw)).toBe(MIB);
    const body = JSON.parse(raw) as unknown;
    const { admission, log, facts } = admissionE({
      a: { standing: ['event:publish'] },
      b: { standing: ['event:publish'] },
    });
    expect(await admission.admit(request('b', body))).toEqual({
      refused: { code: 'invalid_inbound_context' },
    });
    expect(log.events.map((e) => e.reason)).toEqual(['inbound_too_large']);
    expect(facts.calls).toEqual([]);
  });
});

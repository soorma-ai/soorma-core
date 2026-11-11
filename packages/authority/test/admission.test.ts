// SPDX-License-Identifier: FSL-1.1-ALv2
// The entry point end to end: createEnvelopeAdmission(dependencies).admit(
// request). TC-AE-001, 002, 003, 005, 009, 011, 013, 015, 016, 017, 018, 019,
// 021, 022 (rows 1 to 3), 023, 024, 025, 026, 027, 028, 030, 031 step 2;
// D-AE-04, 08, 10, 11, 23, 26; NP-05, NP-08; BR-IN; BR-RF; L1-01, 02, 12,
// 18, 19, 24, 34, 36; I2, I3, I5.
import { canonicalize } from '@soorma/jcs';
import { isProblemCode } from '@soorma/perimeter';
import type { RefusalCode } from '@soorma/envelope';
import { describe, expect, it } from 'vitest';
import type { AdmissionResult, Admitted } from '../src/index.ts';
import {
  admissionE,
  draft,
  E,
  E2,
  envelope,
  padTo,
  request,
  sealed,
  sealerE,
  sealerE2,
  TRACEPARENT,
} from './support.ts';

function admitted(result: AdmissionResult): Admitted {
  if (!('admitted' in result)) throw new Error(`refused: ${JSON.stringify(result.refused)}`);
  return result.admitted;
}

const PUB = { standing: ['event:publish'] };

describe('TC-AE-001: a valid draft is stamped with exactly the platform fields, and sealed', () => {
  it('scope from the credential; autonomous; this hop; the draft trace context', async () => {
    const { admission, log } = admissionE({ a: PUB });
    const a = admitted(await admission.admit(request('a')));
    expect(a.envelope).toEqual({
      envelopeVersion: 1,
      scope: { organization: 'o1', project: 'p1', environment: 'e' },
      originMode: 'autonomous',
      actorChain: [{ agent: 'a', instance: 'a-i' }],
      traceContext: { traceparent: TRACEPARENT },
    });
    expect(a.seal).toMatch(/^v1\.k1\.[A-Za-z0-9_-]{43}$/);
    const bytes = canonicalize(a.envelope).bytes;
    expect(sealerE.verify(a.seal, bytes)).toBe(true);
    expect(bytes.length).toBeLessThanOrEqual(16384);
    expect(a.outcome).toEqual({
      origin: 'autonomous',
      reBroadeningLoadBearing: false,
      actorChain: a.envelope.actorChain,
    });
    expect(log.events).toEqual([]);
  });
});

describe('TC-AE-002, 003: origin from the single read; propagated as the chain grows', () => {
  it('TC-AE-002: origin from the Registration View, never the draft', async () => {
    const { admission, facts } = admissionE({ a: PUB });
    expect(admitted(await admission.admit(request('a'))).envelope.originMode).toBe('autonomous');
    expect(facts.calls).toEqual([{ environment: E, agents: ['a'] }]);
  });

  it('TC-AE-003: A’s entry as received, then B; one read for [B, A]; the new seal verifies', async () => {
    const { admission, facts } = admissionE({ a: PUB, b: PUB });
    const first = admitted(await admission.admit(request('a')));
    facts.calls.length = 0;
    const second = admitted(
      await admission.admit(
        request('b', draft({ inbound: { envelope: first.envelope, seal: first.seal } })),
      ),
    );
    expect(second.envelope.actorChain).toEqual([
      { agent: 'a', instance: 'a-i' },
      { agent: 'b', instance: 'b-i' },
    ]);
    expect(second.envelope.originMode).toBe('autonomous');
    expect(second.envelope.scope).toEqual({ ...E });
    expect(sealerE.verify(second.seal, canonicalize(second.envelope).bytes)).toBe(true);
    expect(facts.calls).toEqual([{ environment: E, agents: ['b'] }]);
  });

  it('TC-AE-003: with a cold cache, one call names the presenter then the upstream agent', async () => {
    const { admission, facts } = admissionE({ a: PUB, b: PUB });
    await admission.admit(request('b', draft({ inbound: sealed(envelope(['a'])) })));
    expect(facts.calls).toEqual([{ environment: E, agents: ['b', 'a'] }]);
  });
});

describe('TC-AE-005, 015, 018, 019, 022: re-broadening through admit', () => {
  const p = 'event:subscribe';
  const forwardA = () => draft({ inbound: sealed(envelope(['a'])) });

  it.each([
    [
      'row 1: in every upstream term',
      { a: { standing: [p] }, b: { standing: [p], declared: [p] } },
      true,
      false,
    ],
    [
      'row 2 (TC-AE-005): missing upstream, declared',
      { a: { standing: [] }, b: { standing: [p], declared: [p] } },
      true,
      true,
    ],
    [
      'row 3 (TC-AE-015): missing upstream, not declared',
      { a: { standing: [] }, b: { standing: [p] } },
      false,
      false,
    ],
  ] as const)('TC-AE-022 %s', async (_, agents, allowed, record) => {
    const { admission, log } = admissionE(agents as never);
    const result = await admission.admit(request('b', forwardA(), { required: [p] }));
    if (!allowed) {
      expect(result).toEqual({ refused: { code: 'forbidden' } });
      expect(log.events.map((e) => e.reason)).toEqual(['authority_denied']);
      return;
    }
    const a = admitted(result);
    expect(a.envelope.reBroadening).toEqual(record ? [{ hop: 1 }] : undefined);
    expect(a.outcome.reBroadeningLoadBearing).toBe(record);
  });

  it('TC-AE-018: B’s record grants D nothing; D’s own declaration is recorded at its hop', async () => {
    const agents = {
      a: { standing: [] },
      b: { standing: [p], declared: [p] },
      d: { standing: [p] },
    };
    const { admission } = admissionE(agents);
    const byB = admitted(await admission.admit(request('b', forwardA(), { required: [p] })));
    const forwardB = draft({ inbound: { envelope: byB.envelope, seal: byB.seal } });
    expect(await admission.admit(request('d', forwardB, { required: [p] }))).toEqual({
      refused: { code: 'forbidden' },
    });

    const declaring = admissionE({ ...agents, d: { standing: [p], declared: [p] } });
    const byD = admitted(
      await declaring.admission.admit(request('d', forwardB, { required: [p] })),
    );
    expect(byD.envelope.reBroadening).toEqual([{ hop: 1 }, { hop: 2 }]);
  });

  it('TC-AE-019: declared but not load-bearing: no record, at a forwarded hop and a first hop', async () => {
    const { admission } = admissionE({
      a: PUB,
      b: { standing: ['event:publish'], declared: ['event:publish'] },
    });
    expect(admitted(await admission.admit(request('b', forwardA()))).envelope).not.toHaveProperty(
      'reBroadening',
    );
    expect(admitted(await admission.admit(request('b'))).envelope).not.toHaveProperty(
      'reBroadening',
    );
  });
});

describe('Refusals through admit: returned, logged once with the reason, never in the response', () => {
  async function refusal(
    agents: Parameters<typeof admissionE>[0],
    req: Parameters<ReturnType<typeof admissionE>['admission']['admit']>[0],
  ) {
    const { admission, log, facts } = admissionE(agents);
    const result = await admission.admit(req);
    expect('refused' in result).toBe(true);
    expect(log.events).toHaveLength(1);
    return { result, event: log.events[0]!, reads: facts.calls.length };
  }

  it('TC-AE-009: a stamped field: stamped_field_set; facts never called', async () => {
    const r = await refusal({ a: PUB }, request('a', draft({ originMode: 'autonomous' })));
    expect(r.result).toEqual({
      refused: { code: 'stamped_field_set', errors: [{ pointer: '/originMode' }] },
    });
    expect(r.reads).toBe(0);
  });

  it('TC-AE-011: no declared autonomy, no inbound: forbidden, o12_undeclared', async () => {
    const r = await refusal({ c: { autonomy: false, standing: ['event:publish'] } }, request('c'));
    expect(r.result).toEqual({ refused: { code: 'forbidden' } });
    expect(r.event).toEqual({
      code: 'forbidden',
      reason: 'o12_undeclared',
      requestId: 'r-1',
      environment: 'e',
      agent: 'c',
      instance: 'c-i',
    });
  });

  it('TC-AE-013, TC-AE-030: step 5 through admit', async () => {
    expect((await refusal({}, request('a', [], {}))).result).toEqual({
      refused: { code: 'malformed_request', errors: [{ pointer: '' }] },
    });
    expect(
      (await refusal({}, request('a', draft({ clientContractVersion: '0.2.0', scope: {} }))))
        .result,
    ).toEqual({
      refused: { code: 'unsupported_contract_version' },
    });
    expect(
      (await refusal({}, request('a', draft(), { header: ['0.1.0', '0.1.0'] }))).result,
    ).toEqual({
      refused: { code: 'malformed_request', errors: [{ header: 'Soorma-Contract-Version' }] },
    });
    const { admission } = admissionE({ a: PUB });
    expect(
      'admitted' in (await admission.admit(request('a', draft(), { header: ['0.1.0'] }))),
    ).toBe(true);
    expect('admitted' in (await admission.admit(request('a', draft(), { header: [] })))).toBe(true);
  });

  it('TC-AE-017: 32 forwarded entries: chain_too_deep, with no read; 31 is admitted as 32', async () => {
    const chain = (n: number) => Array.from({ length: n }, (_, i) => `a${i}`);
    const agents = Object.fromEntries([...chain(32), 'b'].map((a) => [a, PUB]));
    const r = await refusal(agents, request('b', draft({ inbound: sealed(envelope(chain(32))) })));
    expect(r.result).toEqual({ refused: { code: 'chain_too_deep' } });
    expect(r.event.reason).toBe('chain_depth');
    expect(r.reads).toBe(0);
    const { admission } = admissionE(agents);
    const a = admitted(
      await admission.admit(request('b', draft({ inbound: sealed(envelope(chain(31))) }))),
    );
    expect(a.envelope.actorChain).toHaveLength(32);
  });

  it('TC-AE-021: an unresolved upstream agent; an unresolved presenter', async () => {
    const up = await refusal({ b: PUB }, request('b', draft({ inbound: sealed(envelope(['x'])) })));
    expect(up.result).toEqual({ refused: { code: 'forbidden' } });
    expect(up.event.reason).toBe('upstream_unresolved');
    const me = await refusal({}, request('b'));
    expect(me.result).toEqual({ refused: { code: 'forbidden' } });
    expect(me.event.reason).toBe('presenter_unresolved');
  });

  it('TC-AE-016 step 2: an unresolved upstream agent, recovered by the presenter’s declaration', async () => {
    const { admission, log } = admissionE({
      b: { standing: ['event:publish'], declared: ['event:publish'] },
    });
    const a = admitted(
      await admission.admit(request('b', draft({ inbound: sealed(envelope(['x'])) }))),
    );
    expect(a.envelope.reBroadening).toEqual([{ hop: 1 }]);
    expect(a.outcome.reBroadeningLoadBearing).toBe(true);
    expect(log.events).toEqual([]);
  });

  it('TC-AE-023: C, autonomy not declared, forwarding A’s autonomous envelope: forbidden', async () => {
    const agents = { a: PUB, c: { autonomy: false, standing: ['event:publish'] } };
    const r = await refusal(agents, request('c', draft({ inbound: sealed(envelope(['a'])) })));
    expect(r.result).toEqual({ refused: { code: 'forbidden' } });
    expect(r.event.reason).toBe('o12_undeclared');
  });

  it.each([
    [
      '1: a changed character',
      () => ({ envelope: envelope(['b']), seal: sealed(envelope(['a'])).seal }),
      'seal_failed',
    ],
    ['2: sealed with ring(E2)', () => sealed(envelope(['a']), sealerE2), 'seal_failed'],
    [
      '3: a kid not in ring(E)',
      () => ({ envelope: envelope(['a']), seal: `v1.k9.${'A'.repeat(43)}` }),
      'seal_failed',
    ],
    [
      '4: a MAC of 42 characters',
      () => ({ envelope: envelope(['a']), seal: `v1.k1.${'A'.repeat(42)}` }),
      'seal_failed',
    ],
    [
      '5: envelopeVersion 2',
      () => sealed(envelope(['a'], { envelopeVersion: 2 })),
      'envelope_version',
    ],
    ['6: scope naming E2', () => sealed(envelope(['a'], { scope: { ...E2 } })), 'scope_mismatch'],
    [
      '7: a hop outside the chain',
      () => sealed(envelope(['a', 'b'], { reBroadening: [{ hop: 5 }] })),
      'rebroadening_index',
    ],
    ['8: 16385 JCS bytes', () => sealed(padTo(envelope(['a']), 16385)), 'inbound_too_large'],
    [
      '9: a lone surrogate',
      () => ({ envelope: envelope(['a'], { 'x-u': '\ud800' }), seal: 'v1.k1.x' }),
      'jcs_invalid',
    ],
  ])(
    'TC-AE-024 %s: invalid_inbound_context, no detail; facts never called',
    async (_, inbound, reason) => {
      const r = await refusal({ a: PUB, b: PUB }, request('b', draft({ inbound: inbound() })));
      expect(r.result).toEqual({ refused: { code: 'invalid_inbound_context' } });
      expect(r.event.reason).toBe(reason);
      expect(r.reads).toBe(0);
    },
  );

  it('TC-AE-025: a forwarded delegated or unknown origin: forbidden, never a crash', async () => {
    const delegated = envelope(['a'], {
      originMode: 'delegated',
      delegatingPrincipal: { organization: 'o1', principal: 'h@example.com' },
    });
    const unknown = envelope(['a'], { originMode: 'x-future-mode' });
    for (const env of [delegated, unknown]) {
      const r = await refusal({ a: PUB, b: PUB }, request('b', draft({ inbound: sealed(env) })));
      expect(r.result).toEqual({ refused: { code: 'forbidden' } });
      expect(r.event.reason).toBe('origin_unsupported');
    }
  });

  it('TC-AE-026: human-only permissions through admit', async () => {
    const all = ['grant:human', 'human:manage', 'agent:delegate'];
    for (const q of all) {
      const r = await refusal({ a: { standing: all } }, request('a', draft(), { required: [q] }));
      expect(r.result).toEqual({ refused: { code: 'forbidden' } });
      expect(r.event.reason).toBe('human_only_permission');
    }
  });

  it('TC-AE-028: over the bound at stamping: envelope_too_large, after authority', async () => {
    const hop = { agent: 'b', instance: 'b-i' };
    const base = envelope(['a']);
    const stampedAt = (size: number) => {
      const padded = padTo({ ...base, actorChain: [...(base.actorChain as unknown[]), hop] }, size);
      return { ...base, 'x-pad': padded['x-pad'] };
    };
    const { admission } = admissionE({ a: PUB, b: PUB });
    const exact = admitted(
      await admission.admit(request('b', draft({ inbound: sealed(stampedAt(16384)) }))),
    );
    expect(canonicalize(exact.envelope).bytes.length).toBe(16384);
    const r = await refusal(
      { a: PUB, b: PUB },
      request('b', draft({ inbound: sealed(stampedAt(16385)) })),
    );
    expect(r.result).toEqual({ refused: { code: 'envelope_too_large' } });
    expect(r.event.reason).toBe('envelope_bound');
    expect(r.reads).toBe(1);
  });

  it('TC-AE-027: A6 through admit', async () => {
    const { admission } = admissionE({ a: PUB, b: PUB });
    const T1 = '00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01';
    const fwd = sealed(
      envelope(['a'], {
        traceContext: { traceparent: TRACEPARENT, tracestate: 'a=1', 'x-trace-future': 'v' },
      }),
    );
    const a = admitted(
      await admission.admit(
        request('b', draft({ traceContext: { traceparent: T1 }, inbound: fwd })),
      ),
    );
    expect(a.envelope.traceContext).toEqual({ 'x-trace-future': 'v', traceparent: T1 });
  });

  it('D-AE-10, 23: an empty required set, or a scope other than the configured one: internal_error, never an allow', async () => {
    const empty = await refusal({ a: PUB }, request('a', draft(), { required: [] }));
    expect(empty.result).toEqual({ refused: { code: 'internal_error' } });
    expect(empty.event.reason).toBe('empty_required_set');
    const other = await refusal({ a: PUB }, request('a', draft(), { scope: E2 }));
    expect(other.result).toEqual({ refused: { code: 'internal_error' } });
    expect(other.event.reason).toBe('credential_scope_mismatch');
  });

  it('a failed agent-facts read: unavailable with Retry-After 1, never an allow (BR-AU-09)', async () => {
    const { admission, facts, log } = admissionE({ a: PUB });
    facts.failing = true;
    expect(await admission.admit(request('a'))).toEqual({
      refused: { code: 'unavailable', retryAfterSeconds: 1 },
    });
    expect(log.events.map((e) => e.reason)).toEqual(['agent_facts_read_failed']);
  });
});

describe('TC-AE-031 step 2, BR-RF-03: every code admit can return is in P1’s table', () => {
  const codes = [
    'malformed_request',
    'unsupported_contract_version',
    'stamped_field_set',
    'unknown_field',
    'invalid_inbound_context',
    'chain_too_deep',
    'forbidden',
    'unavailable',
    'envelope_too_large',
    'internal_error',
  ] as const satisfies readonly RefusalCode[];
  // Compile-time: the list is every RefusalCode.
  const exhaustive: Exclude<RefusalCode, (typeof codes)[number]> extends never ? true : false =
    true;

  it.each(codes)('%s', (code) => {
    expect(exhaustive).toBe(true);
    expect(isProblemCode(code)).toBe(true);
  });
});

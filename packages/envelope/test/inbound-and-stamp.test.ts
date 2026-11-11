// SPDX-License-Identifier: FSL-1.1-ALv2
// Steps 7, 8 and 10 in P2: TC-AE-001 (P2), 003 (P2), 005 (the record), 008,
// 017, 024 (P2), 027, 028, 037 steps 2, 3; BR-FX; BR-CD; BR-ST; D-AE-05, 13,
// 14, 19, 22; NP-07; L1-01, 03, 05, 16, 18, 29, 32, 37.
import { canonicalize } from '@soorma/jcs';
import { describe, expect, it } from 'vitest';
import {
  checkChainDepth,
  copyJson,
  ENVELOPE_BOUND,
  MAX_CHAIN_DEPTH,
  stamp,
  verifyInbound,
  type ValidDraft,
  type VerifiedInbound,
} from '../src/index.ts';
import {
  E,
  E2,
  envelope,
  padTo,
  sealed,
  sealerE,
  sealerE2,
  TRACEPARENT,
  TRACEPARENT_1,
} from './support.ts';

const draftOf = (traceContext: ValidDraft['traceContext']): ValidDraft => ({
  clientContractVersion: '0.1.0',
  traceContext,
});
const B = { agent: 'b', instance: 'b-i' };

function verified(env: Record<string, unknown>): VerifiedInbound {
  const result = verifyInbound(sealed(env), E, sealerE);
  if (!result.ok) throw new Error(`not verified: ${result.refusal.reason}`);
  return result.value;
}

describe('TC-AE-024 (P2): every forwarded-context failure is one code, with a reason', () => {
  const reason = (inbound: { envelope: Record<string, unknown>; seal: string }) => {
    const r = verifyInbound(inbound, E, sealerE);
    expect(r.ok).toBe(false);
    if (r.ok) return undefined;
    expect(r.refusal.code).toBe('invalid_inbound_context');
    expect(r.refusal.errors).toBeUndefined();
    return r.refusal.reason;
  };

  it('1: one changed character, the seal kept', () => {
    const { seal } = sealed(envelope());
    expect(reason({ envelope: envelope(['b']), seal })).toBe('seal_failed');
  });
  it("2: sealed with another environment's ring", () => {
    expect(reason(sealed(envelope(), sealerE2))).toBe('seal_failed');
  });
  it('5: envelopeVersion 2', () => {
    expect(reason(sealed(envelope(['a'], { envelopeVersion: 2 })))).toBe('envelope_version');
  });
  it('6: scope naming E2', () => {
    expect(reason(sealed(envelope(['a'], { scope: { ...E2 } })))).toBe('scope_mismatch');
  });
  it('7: a hop outside the chain, and a hop twice', () => {
    expect(reason(sealed(envelope(['a', 'b'], { reBroadening: [{ hop: 5 }] })))).toBe(
      'rebroadening_index',
    );
    expect(reason(sealed(envelope(['a', 'b'], { reBroadening: [{ hop: 2 }] })))).toBe(
      'rebroadening_index',
    );
    expect(reason(sealed(envelope(['a', 'b'], { reBroadening: [{ hop: 0 }, { hop: 0 }] })))).toBe(
      'rebroadening_index',
    );
  });
  it('8: 16385 JCS bytes, refused before the seal is computed', () => {
    const big = padTo(envelope(), ENVELOPE_BOUND + 1);
    expect(canonicalize(big).bytes.length).toBe(16385);
    expect(reason({ envelope: big, seal: 'not even a seal' })).toBe('inbound_too_large');
    expect(verifyInbound(sealed(padTo(envelope(), ENVELOPE_BOUND)), E, sealerE).ok).toBe(true);
  });
  it('9: a lone surrogate in an unknown field', () => {
    expect(reason({ envelope: envelope(['a'], { 'x-future': '\ud800' }), seal: 'x' })).toBe(
      'jcs_invalid',
    );
  });
  it('scope comparison is exact, and ignores unknown fields in scope', () => {
    expect(reason(sealed(envelope(['a'], { scope: { ...E, environment: 'E' } })))).toBe(
      'scope_mismatch',
    );
    expect(
      verifyInbound(sealed(envelope(['a'], { scope: { ...E, 'x-s': 1 } })), E, sealerE).ok,
    ).toBe(true);
  });
});

describe('TC-AE-017: maxChainDepth is 32; never truncated (BR-CD)', () => {
  it('31 forwarded entries make 32; 32 forwarded make 33, refused', () => {
    expect(MAX_CHAIN_DEPTH).toBe(32);
    expect(checkChainDepth(31)).toEqual({ ok: true, value: 32 });
    expect(checkChainDepth(32)).toEqual({
      ok: false,
      refusal: { code: 'chain_too_deep', reason: 'chain_depth' },
    });
    expect(checkChainDepth(0)).toEqual({ ok: true, value: 1 });
  });

  it('a 31-entry forwarded chain is stamped as 32, every entry kept', () => {
    const chain = Array.from({ length: 31 }, (_, i) => `a${i}`);
    const r = stamp(
      {
        scope: E,
        actor: B,
        draft: draftOf({ traceparent: TRACEPARENT }),
        inbound: verified(envelope(chain)),
        loadBearing: false,
      },
      sealerE,
    );
    expect(r.ok && (r.value.envelope.actorChain as unknown[]).length).toBe(32);
  });
});

describe('TC-AE-001 (P2): a first hop is stamped with exactly the platform fields', () => {
  it('scope from the context, autonomous, this hop, the draft trace context; nothing else', () => {
    const r = stamp(
      {
        scope: E,
        actor: { agent: 'a', instance: 'a-i' },
        draft: draftOf({ traceparent: TRACEPARENT }),
        loadBearing: false,
      },
      sealerE,
    );
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    expect(r.value.envelope).toEqual({
      envelopeVersion: 1,
      scope: { organization: 'o1', project: 'p1', environment: 'e' },
      originMode: 'autonomous',
      actorChain: [{ agent: 'a', instance: 'a-i' }],
      traceContext: { traceparent: TRACEPARENT },
    });
    expect(r.value.seal).toMatch(/^v1\.k1\.[A-Za-z0-9_-]{43}$/);
    const bytes = canonicalize(r.value.envelope).bytes;
    expect(sealerE.verify(r.value.seal, bytes)).toBe(true);
    expect(r.value.size).toBe(bytes.length);
  });
});

describe('TC-AE-003, 005, 008 (P2): stamping over a forwarded envelope', () => {
  it('TC-AE-003: the forwarded entries as received, then this hop; scope and origin kept', () => {
    const forwarded = envelope(['a']);
    const r = stamp(
      {
        scope: E2,
        actor: B,
        draft: draftOf({ traceparent: TRACEPARENT_1 }),
        inbound: verified(forwarded),
        loadBearing: false,
      },
      sealerE,
    );
    expect(r.ok && r.value.envelope).toEqual({
      ...forwarded,
      actorChain: [{ agent: 'a', instance: 'a-i' }, B],
      traceContext: { traceparent: TRACEPARENT_1 },
    });
  });

  it('TC-AE-005: a load-bearing record is { hop: n }, zero-based in the new chain', () => {
    const r = stamp(
      {
        scope: E,
        actor: B,
        draft: draftOf({ traceparent: TRACEPARENT }),
        inbound: verified(envelope(['a'])),
        loadBearing: true,
      },
      sealerE,
    );
    expect(r.ok && r.value.envelope.reBroadening).toEqual([{ hop: 1 }]);
  });

  it("TC-AE-018 (P2): a forwarded record is carried unchanged, then this hop's", () => {
    const r = stamp(
      {
        scope: E,
        actor: { agent: 'd', instance: 'd-i' },
        draft: draftOf({ traceparent: TRACEPARENT }),
        inbound: verified(envelope(['a', 'b'], { reBroadening: [{ hop: 1, 'x-r': true }] })),
        loadBearing: true,
      },
      sealerE,
    );
    expect(r.ok && r.value.envelope.reBroadening).toEqual([{ hop: 1, 'x-r': true }, { hop: 2 }]);
  });

  it('TC-AE-008: unknown fields at every level U3 does not replace are kept', () => {
    const forwarded = envelope(['a'], {
      'x-future': { nested: [1, 'two', null] },
      scope: { ...E, 'x-scope': 's' },
      actorChain: [{ agent: 'a', instance: 'a-i', 'x-actor': 'a' }],
      reBroadening: [{ hop: 0, 'x-record': 'r' }],
    });
    const r = stamp(
      {
        scope: E,
        actor: B,
        draft: draftOf({ traceparent: TRACEPARENT }),
        inbound: verified(forwarded),
        loadBearing: false,
      },
      sealerE,
    );
    if (!r.ok) throw new Error(r.refusal.reason);
    expect(r.value.envelope['x-future']).toEqual({ nested: [1, 'two', null] });
    expect(r.value.envelope.scope).toEqual({ ...E, 'x-scope': 's' });
    expect((r.value.envelope.actorChain as unknown[])[0]).toEqual({
      agent: 'a',
      instance: 'a-i',
      'x-actor': 'a',
    });
    expect(r.value.envelope.reBroadening).toEqual([{ hop: 0, 'x-record': 'r' }]);
  });

  it('the forwarded envelope is not changed by stamping', () => {
    const forwarded = envelope(['a']);
    const before = canonicalize(forwarded).text;
    stamp(
      {
        scope: E,
        actor: B,
        draft: draftOf({ traceparent: TRACEPARENT }),
        inbound: verified(forwarded),
        loadBearing: true,
      },
      sealerE,
    );
    expect(canonicalize(forwarded).text).toBe(before);
  });
});

describe('TC-AE-027: the stamped trace context, by U1 amendment A6 (D-AE-05)', () => {
  const forwarded = envelope(['a'], {
    traceContext: { traceparent: TRACEPARENT, tracestate: 'a=1', 'x-trace-future': 'v' },
  });
  it('1: the draft sends no tracestate: none is carried', () => {
    const r = stamp(
      {
        scope: E,
        actor: B,
        draft: draftOf({ traceparent: TRACEPARENT_1 }),
        inbound: verified(forwarded),
        loadBearing: false,
      },
      sealerE,
    );
    expect(r.ok && r.value.envelope.traceContext).toEqual({
      'x-trace-future': 'v',
      traceparent: TRACEPARENT_1,
    });
  });
  it("2: the draft's tracestate, never the forwarded one", () => {
    const r = stamp(
      {
        scope: E,
        actor: B,
        draft: draftOf({ traceparent: TRACEPARENT_1, tracestate: 'b=2' }),
        inbound: verified(forwarded),
        loadBearing: false,
      },
      sealerE,
    );
    expect(r.ok && r.value.envelope.traceContext).toEqual({
      'x-trace-future': 'v',
      traceparent: TRACEPARENT_1,
      tracestate: 'b=2',
    });
  });
});

describe('TC-AE-028: over the bound at stamping, refused and never truncated', () => {
  const hop = { agent: 'b', instance: 'b-i' };
  // Pad the forwarded envelope so that the stamped one lands on a given size.
  function forwardedFor(stampedSize: number, loadBearing: boolean): Record<string, unknown> {
    const base = envelope(['a']);
    const stamped = {
      ...base,
      actorChain: [...(base.actorChain as unknown[]), hop],
      ...(loadBearing ? { reBroadening: [{ hop: 1 }] } : {}),
    };
    const padded = padTo(stamped, stampedSize);
    return { ...base, 'x-pad': padded['x-pad'] };
  }
  const run = (forwarded: Record<string, unknown>, loadBearing: boolean) =>
    stamp(
      {
        scope: E,
        actor: hop,
        draft: draftOf({ traceparent: TRACEPARENT }),
        inbound: verified(forwarded),
        loadBearing,
      },
      sealerE,
    );

  it('1: exactly 16384 bytes is admitted', () => {
    const r = run(forwardedFor(ENVELOPE_BOUND, false), false);
    expect(r.ok && r.value.size).toBe(16384);
  });
  it('2: 16385 bytes is envelope_too_large', () => {
    expect(run(forwardedFor(ENVELOPE_BOUND + 1, false), false)).toEqual({
      ok: false,
      refusal: { code: 'envelope_too_large', reason: 'envelope_bound' },
    });
  });
  it("3: this hop's load-bearing record is what crosses the bound", () => {
    const forwarded = forwardedFor(ENVELOPE_BOUND, false);
    expect(run(forwarded, false).ok).toBe(true);
    expect(run(forwarded, true)).toMatchObject({
      ok: false,
      refusal: { code: 'envelope_too_large' },
    });
  });
});

describe('TC-AE-037 steps 2, 3: the copy defines own properties; __proto__ is a field (NP-07)', () => {
  it('copies a __proto__ key as an own property and never sets a prototype', () => {
    const original = JSON.parse('{"__proto__": {"polluted": true}, "a": 1}') as Record<
      string,
      unknown
    >;
    const copy = copyJson(original);
    expect(Object.getPrototypeOf(copy)).toBe(Object.prototype);
    expect(Object.hasOwn(copy, '__proto__')).toBe(true);
    expect(({} as Record<string, unknown>).polluted).toBeUndefined();
    expect((copy as { polluted?: unknown }).polluted).toBeUndefined();
    expect(canonicalize(copy).bytes.equals(canonicalize(original).bytes)).toBe(true);
  });

  it('copies 100,000 levels without recursion, and shares nothing with the original', () => {
    let deep: unknown = 'leaf';
    for (let i = 0; i < 100_000; i++) deep = i % 2 ? { k: deep } : [deep];
    const copy = copyJson(deep);
    expect(copy === deep).toBe(false); // a plain comparison: Vitest walks a value it formats
    expect(canonicalize(copy).text).toBe(canonicalize(deep).text);
  });
});

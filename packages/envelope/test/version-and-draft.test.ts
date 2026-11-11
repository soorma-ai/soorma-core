// SPDX-License-Identifier: FSL-1.1-ALv2
// Steps 5 and 6: TC-AE-007, 009, 010, 012, 013, 014, 029, 030; BR-VR-01 to
// 05; BR-DV-01 to 05; D-AE-12, 17, 18; L1-02, 16, 23, 27, 31, 33.
import { readdirSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { checkVersion, createDraftValidator, MAX_ERRORS, STAMPED_FIELDS } from '../src/index.ts';
import { draft, envelope, TRACEPARENT } from './support.ts';

const ACCEPTED = ['0.1.0'];
const validator = createDraftValidator();
const validate = (d: Record<string, unknown>) => validator.validate(d);

describe('TC-AE-013, TC-AE-030: step 5 on a call with a draft (BR-VR)', () => {
  it.each([[[]], ['x'], [null], [7]])(
    'a body that is not an object (%j): malformed_request at ""',
    (body) => {
      expect(checkVersion(body, [], ACCEPTED)).toEqual({
        ok: false,
        refusal: {
          code: 'malformed_request',
          reason: 'body_not_object',
          errors: [{ pointer: '' }],
        },
      });
    },
  );

  it('TC-AE-013: no version, or a non-string one, is unsupported_contract_version', () => {
    const none = draft();
    delete none.clientContractVersion;
    for (const body of [none, draft({ clientContractVersion: 1 })])
      expect(checkVersion(body, [], ACCEPTED)).toEqual({
        ok: false,
        refusal: { code: 'unsupported_contract_version', reason: 'version_missing' },
      });
  });

  it('a version not accepted, by exact match', () => {
    for (const v of ['0.2.0', 'v0.1.0', '0.1', '0.1.0 '])
      expect(checkVersion(draft({ clientContractVersion: v }), [], ACCEPTED)).toEqual({
        ok: false,
        refusal: { code: 'unsupported_contract_version', reason: 'version_not_accepted' },
      });
  });

  it('the header: different, or sent twice, is malformed_request naming it', () => {
    const refused = {
      ok: false,
      refusal: {
        code: 'malformed_request',
        reason: 'version_header_mismatch',
        errors: [{ header: 'Soorma-Contract-Version' }],
      },
    };
    expect(checkVersion(draft(), ['0.1.1'], ACCEPTED)).toEqual(refused);
    expect(checkVersion(draft(), ['0.1.0', '0.1.0'], ACCEPTED)).toEqual(refused);
    expect(checkVersion(draft(), ['0.1.0'], ACCEPTED).ok).toBe(true);
    expect(checkVersion(draft(), [], ACCEPTED).ok).toBe(true);
  });

  it('step 5 runs before step 6, and reads only the version', () => {
    expect(
      checkVersion(draft({ clientContractVersion: '0.2.0', scope: {} }), [], ACCEPTED),
    ).toMatchObject({ ok: false, refusal: { code: 'unsupported_contract_version' } });
    expect(checkVersion(draft({ scope: {}, foo: 1 }), [], ACCEPTED).ok).toBe(true);
  });

  it('a version reached only through the prototype is not read', () => {
    const body = Object.create({ clientContractVersion: '0.1.0' }) as Record<string, unknown>;
    expect(checkVersion(body, [], ACCEPTED)).toMatchObject({
      refusal: { reason: 'version_missing' },
    });
  });
});

describe('TC-AE-009, 010, 014: a draft setting a platform-stamped field (BR-DV-02, 04)', () => {
  it.each(STAMPED_FIELDS)('%s: stamped_field_set, one pointer', (field) => {
    expect(validate(draft({ [field]: field === 'originMode' ? 'autonomous' : [] }))).toEqual({
      ok: false,
      refusal: {
        code: 'stamped_field_set',
        reason: 'stamped_field',
        errors: [{ pointer: `/${field}` }],
      },
    });
  });
});

describe('TC-AE-007: a well-formed trace context is accepted as asserted', () => {
  it.each([
    [
      'version 00 with tracestate',
      { traceparent: TRACEPARENT, tracestate: 'rojo=00f067aa0ba902b7,congo=t61rcWkgMzE' },
    ],
    [
      'version 01 with a further field',
      { traceparent: `01-${TRACEPARENT.slice(3)}-what-the-future-holds` },
    ],
    [
      '32 tracestate members',
      {
        traceparent: TRACEPARENT,
        tracestate: Array.from({ length: 32 }, (_, i) => `k${i}=v`).join(','),
      },
    ],
    ['multi-tenant keys', { traceparent: TRACEPARENT, tracestate: 'tenant1@sys=v, t-2*/x@abc=w' }],
  ])('%s', (_, traceContext) => {
    const result = validate(draft({ traceContext }));
    expect(result).toEqual({ ok: true, value: draft({ traceContext }) });
  });
});

describe('TC-AE-012: a malformed trace context (D-AE-17)', () => {
  const bad = (traceContext: Record<string, unknown>) => validate(draft({ traceContext }));
  it.each([
    [
      'the wrong length',
      { traceparent: TRACEPARENT.slice(0, -1) },
      '/traceContext/traceparent',
      'schema',
    ],
    [
      'version 00 with an extra field',
      { traceparent: `${TRACEPARENT}-x` },
      '/traceContext/traceparent',
      'schema',
    ],
    [
      'version ff',
      { traceparent: `ff-${TRACEPARENT.slice(3)}` },
      '/traceContext/traceparent',
      'trace_context',
    ],
    [
      'an all-zero trace id',
      { traceparent: `00-${'0'.repeat(32)}-00f067aa0ba902b7-01` },
      '/traceContext/traceparent',
      'trace_context',
    ],
    [
      'an all-zero parent id',
      { traceparent: `00-4bf92f3577b34da6a3ce929d0e0e4736-${'0'.repeat(16)}-01` },
      '/traceContext/traceparent',
      'trace_context',
    ],
    [
      'uppercase hex',
      { traceparent: TRACEPARENT.toUpperCase() },
      '/traceContext/traceparent',
      'schema',
    ],
    [
      '33 tracestate members',
      {
        traceparent: TRACEPARENT,
        tracestate: Array.from({ length: 33 }, (_, i) => `k${i}=v`).join(','),
      },
      '/traceContext/tracestate',
      'trace_context',
    ],
    [
      'an invalid tracestate key',
      { traceparent: TRACEPARENT, tracestate: 'Upper=v' },
      '/traceContext/tracestate',
      'trace_context',
    ],
    [
      'a tracestate over 512 characters',
      { traceparent: TRACEPARENT, tracestate: `k=${'v'.repeat(511)}` },
      '/traceContext/tracestate',
      'schema',
    ],
  ])('%s', (_, traceContext, pointer, reason) => {
    const result = bad(traceContext);
    expect(result).toMatchObject({ ok: false, refusal: { code: 'malformed_request', reason } });
    if (!result.ok) expect(result.refusal.errors?.map((e) => e.pointer)).toEqual([pointer]);
  });
});

describe('TC-AE-029: one code, in a fixed precedence, every failing field ordered by pointer', () => {
  const malformed = { traceparent: 'bad' };
  it('1: a stamped field wins over unknown and malformed', () => {
    expect(validate(draft({ scope: {}, foo: 1, traceContext: malformed }))).toEqual({
      ok: false,
      refusal: {
        code: 'stamped_field_set',
        reason: 'stamped_field',
        errors: [{ pointer: '/scope' }],
      },
    });
  });
  it('2: unknown fields win over malformed, ordered by pointer', () => {
    expect(validate(draft({ foo: 1, bar: 2, traceContext: malformed }))).toEqual({
      ok: false,
      refusal: {
        code: 'unknown_field',
        reason: 'unknown_field',
        errors: [{ pointer: '/bar' }, { pointer: '/foo' }],
      },
    });
  });
  it('3: an unknown field inside traceContext', () => {
    expect(validate(draft({ traceContext: { traceparent: TRACEPARENT, baggage: 'x' } }))).toEqual({
      ok: false,
      refusal: {
        code: 'unknown_field',
        reason: 'unknown_field',
        errors: [{ pointer: '/traceContext/baggage' }],
      },
    });
  });
  it('4: only a malformed traceparent', () => {
    expect(validate(draft({ traceContext: malformed }))).toMatchObject({
      ok: false,
      refusal: { code: 'malformed_request', errors: [{ pointer: '/traceContext/traceparent' }] },
    });
  });
  it('an unknown field in the inbound wrapper is malformed_request, not unknown_field', () => {
    expect(
      validate(draft({ inbound: { envelope: envelope(), seal: 'v1.k1.x', extra: 1 } })),
    ).toMatchObject({
      refusal: { code: 'malformed_request', errors: [{ pointer: '/inbound/extra' }] },
    });
  });
});

describe('TC-AE-029 step 5: errors[] holds at most 10 entries, the first by pointer (D-AE-18)', () => {
  const names = (n: number) =>
    Array.from({ length: n }, (_, i) => `f${String(i).padStart(2, '0')}`).reverse();
  it('15 unknown fields and a malformed traceparent: unknown_field, the first 10 by pointer', () => {
    const fields = Object.fromEntries(names(15).map((f) => [f, 1]));
    const result = validate(draft({ ...fields, traceContext: { traceparent: 'bad' } }));
    expect(MAX_ERRORS).toBe(10);
    expect(result).toEqual({
      ok: false,
      refusal: {
        code: 'unknown_field',
        reason: 'unknown_field',
        errors: names(10)
          .reverse()
          .map((f) => ({ pointer: `/${f}` })),
      },
    });
  });
  it('12 malformed fields: malformed_request, the first 10 by pointer', () => {
    const extra = Object.fromEntries(names(12).map((f) => [f, 1]));
    const result = validate(
      draft({ inbound: { envelope: envelope(), seal: 'v1.k1.x', ...extra } }),
    );
    expect(result).toMatchObject({ ok: false, refusal: { code: 'malformed_request' } });
    if (!result.ok)
      expect(result.refusal.errors?.map((e) => e.pointer)).toEqual(
        names(10)
          .reverse()
          .map((f) => `/inbound/${f}`),
      );
  });
  it('the winning code is picked from every error, not from the first 10', () => {
    // 12 malformed fields sort before the one unknown field, which still wins.
    const extra = Object.fromEntries(names(12).map((f) => [f, 1]));
    expect(
      validate(draft({ inbound: { envelope: envelope(), seal: 'v1.k1.x', ...extra }, zz: 1 })),
    ).toEqual({
      ok: false,
      refusal: { code: 'unknown_field', reason: 'unknown_field', errors: [{ pointer: '/zz' }] },
    });
  });
});

describe("U1's draft and inbound fixtures pass and fail as classified", () => {
  const require = createRequire(import.meta.url);
  const root = dirname(require.resolve('@soorma/contract/envelope.schema.json'));
  const read = (dir: string) =>
    readdirSync(join(root, dir)).map(
      (f) =>
        [
          f,
          JSON.parse(readFileSync(join(root, dir, f), 'utf8')) as Record<string, unknown>,
        ] as const,
    );

  it.each(read('fixtures/0.1.0/draft/valid'))('valid: %s', (_, fixture) => {
    expect(validate(fixture).ok).toBe(true);
  });
  it.each(read('fixtures/0.1.0/draft/invalid'))('invalid: %s', (_, fixture) => {
    expect(validate(fixture).ok).toBe(false);
  });
  it.each(read('fixtures/0.1.0/inbound/invalid'))('invalid inbound: %s', (_, fixture) => {
    expect(validate(draft({ inbound: fixture })).ok).toBe(false);
  });
});

// SPDX-License-Identifier: FSL-1.1-ALv2
// The Body Form (U7 D-ET-01; NP-ET-06; D-CG-ET-18, 20; BR-BF-03 to 05, 07):
// TC-ET-077, and TC-ET-025's cases in process. A stub measure stands in for
// S4's (jcs's source mode), which S4's own tests cover. U3's tests are
// unchanged apart from TC-AE-031's one approved item (payload_too_large).
import type { BodyForm, EnvelopeRequest, MemberMeasure } from '../src/index.ts';
import { describe, expect, it } from 'vitest';
import { admissionE, draft, request } from './support.ts';

const PUB = { standing: ['event:publish'] };
const SUB = { standing: ['event:subscribe'] };

/** A stub: a string's length in bytes; the string 'BAD' has no form at '/x'. */
const stub: MemberMeasure = (value) =>
  value === 'BAD' ? { invalid: '/x' } : { bytes: Buffer.byteLength(JSON.stringify(value)) };

const PUBLISH: BodyForm = {
  draft: 'draft',
  members: [{ name: 'payload', measure: stub, maxBytes: 12 }],
};
const SUBSCRIBE: BodyForm = { draft: 'draft', members: [] };

const withForm = (
  form: BodyForm,
  body: unknown,
  options: Parameters<typeof request>[2] = {},
): EnvelopeRequest => ({ ...request('a', body, options), bodyForm: form });

async function admit(
  form: BodyForm,
  body: unknown,
  options: Parameters<typeof request>[2] = {},
): Promise<{ result: unknown; reasons: string[] }> {
  const { admission, log } = admissionE({ a: form === PUBLISH ? PUB : SUB });
  const required = form === PUBLISH ? ['event:publish'] : ['event:subscribe'];
  const result = await admission.admit(withForm(form, body, { required, ...options }));
  return { result, reasons: log.events.map((e) => e.reason) };
}

describe('TC-ET-077: step 5 with a Body Form', () => {
  it('a body that is not an object: malformed_request at the root', async () => {
    expect((await admit(PUBLISH, [draft()])).result).toEqual({
      refused: { code: 'malformed_request', errors: [{ pointer: '' }] },
    });
  });

  it('no draft member, or one that is not an object: malformed_request at /draft', async () => {
    for (const body of [{ payload: 1 }, { draft: 'x', payload: 1 }, { draft: null, payload: 1 }])
      expect((await admit(PUBLISH, body)).result).toEqual({
        refused: { code: 'malformed_request', errors: [{ pointer: '/draft' }] },
      });
  });

  it("the version is read in the draft member, before the body's schema (TC-ET-025)", async () => {
    const noVersion = { draft: { traceContext: draft().traceContext }, payload: 1, extra: 1 };
    expect((await admit(PUBLISH, noVersion)).result).toMatchObject({
      refused: { code: 'unsupported_contract_version' },
    });
    const notAccepted = { draft: draft({ clientContractVersion: '9.9.9' }), payload: 1 };
    expect((await admit(PUBLISH, notAccepted)).result).toMatchObject({
      refused: { code: 'unsupported_contract_version' },
    });
    const header = await admit(PUBLISH, { draft: draft(), payload: 1 }, { header: ['0.2.0'] });
    expect(header.result).toEqual({
      refused: {
        code: 'malformed_request',
        errors: [{ header: 'Soorma-Contract-Version' }],
      },
    });
  });
});

describe('TC-ET-077: step 6, the members with the draft under the precedence', () => {
  it('an unknown member is unknown_field at its pointer', async () => {
    expect((await admit(PUBLISH, { draft: draft(), payload: 1, extra: 1 })).result).toEqual({
      refused: { code: 'unknown_field', errors: [{ pointer: '/extra' }] },
    });
  });

  it('a missing member is malformed_request at its pointer', async () => {
    expect((await admit(PUBLISH, { draft: draft() })).result).toEqual({
      refused: { code: 'malformed_request', errors: [{ pointer: '/payload' }] },
    });
  });

  it('a stamped field wins over an unknown member, pointed from the root', async () => {
    const body = { draft: draft({ scope: {} }), payload: 1, extra: 1 };
    expect((await admit(PUBLISH, body)).result).toEqual({
      refused: { code: 'stamped_field_set', errors: [{ pointer: '/draft/scope' }] },
    });
  });

  it("the draft's unknown fields and the body's are listed together, by pointer", async () => {
    const body = { draft: draft({ zz: 1 }), payload: 1, aa: 1 };
    expect((await admit(PUBLISH, body)).result).toEqual({
      refused: { code: 'unknown_field', errors: [{ pointer: '/aa' }, { pointer: '/draft/zz' }] },
    });
  });

  it("the draft's other failures and a missing member are listed together", async () => {
    const body = { draft: draft({ traceContext: { traceparent: 'nope' } }) };
    const { result } = await admit(PUBLISH, body);
    expect(result).toMatchObject({ refused: { code: 'malformed_request' } });
    const pointers = (result as { refused: { errors: { pointer: string }[] } }).refused.errors.map(
      (e) => e.pointer,
    );
    expect(pointers).toContain('/payload');
    expect(pointers.some((p) => p.startsWith('/draft/traceContext'))).toBe(true);
    expect([...pointers].sort()).toEqual(pointers);
  });

  it('at most 10 errors, the first by pointer', async () => {
    const extras = Object.fromEntries(Array.from({ length: 12 }, (_, i) => [`x${i + 10}`, 1]));
    const { result } = await admit(PUBLISH, { draft: draft(), payload: 1, ...extras });
    const errors = (result as { refused: { errors: { pointer: string }[] } }).refused.errors;
    expect(errors.map((e) => e.pointer)).toEqual(
      Array.from({ length: 10 }, (_, i) => `/x${i + 10}`),
    );
  });

  it('the subscribe form refuses a payload member as unknown', async () => {
    expect((await admit(SUBSCRIBE, { draft: draft(), payload: 1 })).result).toEqual({
      refused: { code: 'unknown_field', errors: [{ pointer: '/payload' }] },
    });
  });
});

describe("TC-ET-077: then each member's bound, through the caller's measure", () => {
  it('the limit is admitted; the limit plus one byte is payload_too_large', async () => {
    // JSON.stringify('1234567890') is 12 bytes: exactly the stub bound.
    expect((await admit(PUBLISH, { draft: draft(), payload: '1234567890' })).result).toHaveProperty(
      'admitted',
    );
    const over = await admit(PUBLISH, { draft: draft(), payload: '12345678901' });
    expect(over.result).toEqual({
      refused: { code: 'payload_too_large', errors: [{ pointer: '/payload' }] },
    });
    expect(over.reasons).toEqual(['member_too_large']);
  });

  it("a value the measure cannot measure is malformed_request at the measure's pointer", async () => {
    const r = await admit(PUBLISH, { draft: draft(), payload: 'BAD' });
    expect(r.result).toEqual({
      refused: { code: 'malformed_request', errors: [{ pointer: '/payload/x' }] },
    });
    expect(r.reasons).toEqual(['member_invalid']);
  });

  it('the schema is judged before the bound', async () => {
    const body = { draft: draft({ scope: {} }), payload: '12345678901' };
    expect((await admit(PUBLISH, body)).result).toMatchObject({
      refused: { code: 'stamped_field_set' },
    });
  });

  it('an admitted publish stamps the draft member, and logs nothing', async () => {
    const r = await admit(PUBLISH, { draft: draft(), payload: 1 });
    expect(r.result).toMatchObject({
      admitted: { envelope: { originMode: 'autonomous', actorChain: [{ agent: 'a' }] } },
    });
    expect(r.reasons).toEqual([]);
  });

  it('a subscribe body with only its draft is admitted', async () => {
    expect((await admit(SUBSCRIBE, { draft: draft() })).result).toHaveProperty('admitted');
  });
});

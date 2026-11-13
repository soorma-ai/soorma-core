// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S4's refusals, each through the real edge (business-logic-model §8):
// TC-ET-006 (in process), 007, 008, 009, 010, 011, 012, 013, 019, 021, 024,
// 025, 027, 044, 050, 051, 052, 073, 090; the body form's other cases. Every
// Problem goes through the shared Problem assertion (BR-PE-ET-02), and no
// refused request delivers anything, opens a stream, or writes a record.
import { request as httpRequest } from 'node:http';
import { canonicalize } from '@soorma/jcs';
import { assertProblem } from '@soorma/perimeter/testing';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import { ringE, sealed } from '../../../packages/authority/test/support.ts';
import {
  agentKeys,
  agentWith,
  credential,
  draft,
  E,
  E2,
  flush,
  ingest,
  publish,
  PUBLISH,
  PUBLISHER,
  records,
  send,
  SUBSCRIBE,
  subscribe,
  subscribeRefused,
  SUBSCRIBER,
  TRACEPARENT,
  type Credential,
  type Ingest,
  type Response,
  type SseClient,
} from './support.ts';

let db: TestEnvDatabase;
let g: Ingest;
/** A stream open throughout: no refused publish may reach it. */
let watcher: SseClient;

beforeAll(async () => {
  db = await testEnvDatabase();
  // E's seal ring is U3's test ring, so U3's helpers seal as E would (TC-ET-019).
  g = await ingest(db, { seal: ringE });
  await g.listen();
  watcher = await subscribe(g, await agentWith(g, SUBSCRIBER));
});
afterAll(async () => {
  watcher?.destroy();
  await g?.close();
  await db?.drop();
});

/** The Problem is well-formed, and nothing was delivered. */
async function refusedWith(r: Response, status: number, code: string): Promise<void> {
  expect({ status: r.status, code: r.body?.code }).toEqual({ status, code });
  assertProblem({ status: r.status, headers: r.headers, body: r.body }, { status, code });
  await flush(g);
  expect(watcher.events).toEqual([]);
}

describe('steps 2 and 3: the presenter, by kind, never verified (BR-PR-ET-01)', () => {
  it('TC-ET-012: a human credential, of either kind, is credential_refused', async () => {
    for (const token of ['soorma_ec_AAAA.BBBB.CCCC', 'soorma_si_AAAA.BBBB.CCCC']) {
      const r = await publish(g, token);
      await refusedWith(r, 401, 'credential_refused');
      expect(r.headers['www-authenticate']).toBe('Bearer');
    }
    const reasons = g.log.named('ingest.refused').map((e) => e.reason);
    expect(reasons).toContain('presenter');
  });

  it('TC-ET-013: an agent credential beside Soorma-Delegation', async () => {
    const a = await agentWith(g, PUBLISHER);
    const r = await publish(g, a, {}, { headers: { 'soorma-delegation': 'soorma_dc_x' } });
    await refusedWith(r, 401, 'credential_refused');
  });

  it('none, two credentials, an unknown prefix', async () => {
    const a = await agentWith(g, PUBLISHER);
    await refusedWith(
      await send(g.edge, PUBLISH, { body: { draft: draft(), payload: 1 } }),
      401,
      'credential_refused',
    );
    // P1 counts credentials on the raw header list: two are refused by kind.
    const two = await twoCredentials(a.token);
    expect(two).toEqual({ status: 401, code: 'credential_refused' });
    await refusedWith(await publish(g, 'soorma_xx_AAAA'), 401, 'credential_refused');
  });

  it('TC-ET-021: a malformed token with a header claiming prior validation', async () => {
    const r = await publish(
      g,
      'soorma_ac_not.a.token',
      {},
      {
        headers: { 'x-soorma-validated': 'true' },
      },
    );
    await refusedWith(r, 401, 'credential_refused');
  });

  it('TC-ET-027: a forwarded envelope is never a credential', async () => {
    const r = await send(g.edge, PUBLISH, {
      body: { draft: draft({ inbound: { envelope: {}, seal: 'x' } }), payload: 1 },
    });
    await refusedWith(r, 401, 'credential_refused');
  });

  it('a credential signed by another environment’s key is refused, never expired', async () => {
    const a = await agentWith(g, PUBLISHER);
    const foreign = await credential(g, a.agent, { keys: agentKeys(), lifetimeMs: -1_000 });
    await refusedWith(await publish(g, foreign), 401, 'credential_refused');
  });

  it('an expired credential that verifies is credential_expired', async () => {
    const a = await agentWith(g, PUBLISHER);
    const old = await credential(g, a.agent, {
      issuedAt: new Date(g.clock.ms - 20 * 60_000),
      lifetimeMs: 15 * 60_000,
    });
    await refusedWith(await publish(g, old), 401, 'credential_expired');
  });
});

describe('step 4: O4, the environment (TC-ET-006, in process)', () => {
  it('a credential for E2, verified by the same key, is credential_refused at E', async () => {
    const a = await agentWith(g, PUBLISHER);
    const forE2 = await credential(g, a.agent, { env: E2 });
    await refusedWith(await publish(g, forE2), 401, 'credential_refused');
    await refusedWith(await subscribeRefused(g, forE2), 401, 'credential_refused');
  });
});

describe('step 5: the body form and the version (TC-ET-025)', () => {
  let a: Credential;
  let b: Credential;
  beforeAll(async () => {
    a = await agentWith(g, PUBLISHER);
    b = await agentWith(g, SUBSCRIBER);
  });

  it('a missing or unsupported version is unsupported_contract_version, at both operations', async () => {
    for (const d of [
      { traceContext: { traceparent: TRACEPARENT } },
      draft({ clientContractVersion: '9.9.9' }),
    ]) {
      const p = await publish(g, a, {}, { draft: d });
      await refusedWith(p, 400, 'unsupported_contract_version');
      expect(p.body.supportedVersions).toEqual(['0.1.0']);
      await refusedWith(
        await subscribeRefused(g, b, { draft: d }),
        400,
        'unsupported_contract_version',
      );
    }
  });

  it('a header differing from the draft is malformed_request, naming the header', async () => {
    const h = { 'soorma-contract-version': '0.2.0' };
    const p = await publish(g, a, {}, { headers: h });
    await refusedWith(p, 400, 'malformed_request');
    expect(p.body.errors).toEqual([expect.objectContaining({ header: 'Soorma-Contract-Version' })]);
    await refusedWith(await subscribeRefused(g, b, { headers: h }), 400, 'malformed_request');
  });

  it('a body not an object: pointer ""; a draft not an object: pointer /draft', async () => {
    for (const [raw, pointer] of [
      ['[1]', ''],
      ['"x"', ''],
      ['{"draft":"0.1.0","payload":{}}', '/draft'],
      ['{"payload":{}}', '/draft'],
    ] as const) {
      const p = await publish(g, a, undefined, { raw });
      await refusedWith(p, 400, 'malformed_request');
      expect(p.body.errors).toEqual([expect.objectContaining({ pointer })]);
    }
    const s = await subscribeRefused(g, b, { raw: '{"draft":[]}' });
    await refusedWith(s, 400, 'malformed_request');
    expect(s.body.errors).toEqual([expect.objectContaining({ pointer: '/draft' })]);
  });

  it('not JSON at all: malformed_request at ""', async () => {
    for (const raw of ['{', 'not json']) {
      const p = await publish(g, a, undefined, { raw });
      await refusedWith(p, 400, 'malformed_request');
      expect(p.body.errors[0].pointer).toBe('');
    }
  });
});

describe('step 6: the body and the draft judged together (TC-ET-007, 008, 024)', () => {
  let a: Credential;
  beforeAll(async () => {
    a = await agentWith(g, PUBLISHER);
  });

  it('TC-ET-007: each stamped field is stamped_field_set at /draft/<field>', async () => {
    for (const field of [
      'envelopeVersion',
      'scope',
      'originMode',
      'delegatingPrincipal',
      'actorChain',
      'reBroadening',
    ]) {
      const p = await publish(g, a, {}, { draft: draft({ [field]: 1 }) });
      await refusedWith(p, 400, 'stamped_field_set');
      expect(p.body.errors[0].pointer).toBe(`/draft/${field}`);
    }
  });

  it('TC-ET-008: a draft asserting autonomous is stamped_field_set at /draft/originMode', async () => {
    const p = await publish(g, a, {}, { draft: draft({ originMode: 'autonomous' }) });
    await refusedWith(p, 400, 'stamped_field_set');
    expect(p.body.errors[0].pointer).toBe('/draft/originMode');
  });

  it('the precedence holds across the body: stamped over unknown over malformed', async () => {
    const both = await publish(g, a, undefined, {
      raw: JSON.stringify({ draft: draft({ scope: {} }), extra: 1 }),
    });
    await refusedWith(both, 400, 'stamped_field_set');
    const unknown = await publish(g, a, undefined, {
      raw: JSON.stringify({ draft: draft({ topic: 't' }), extra: 1 }),
    });
    await refusedWith(unknown, 400, 'unknown_field');
    expect((unknown.body.errors as { pointer: string }[]).map((e) => e.pointer)).toEqual([
      '/draft/topic',
      '/extra',
    ]);
  });

  it('TC-ET-024: a publish without payload, or with an extra member', async () => {
    const missing = await publish(g, a, undefined, { raw: JSON.stringify({ draft: draft() }) });
    await refusedWith(missing, 400, 'malformed_request');
    expect(missing.body.errors).toEqual([expect.objectContaining({ pointer: '/payload' })]);
    const extra = await publish(g, a, undefined, {
      raw: JSON.stringify({ draft: draft(), payload: 1, topic: 't' }),
    });
    await refusedWith(extra, 400, 'unknown_field');
    expect(extra.body.errors).toEqual([expect.objectContaining({ pointer: '/topic' })]);
  });

  it('a subscribe with a payload is unknown_field at /payload', async () => {
    const b = await agentWith(g, SUBSCRIBER);
    const s = await subscribeRefused(g, b, {
      raw: JSON.stringify({ draft: draft(), payload: {} }),
    });
    await refusedWith(s, 400, 'unknown_field');
    expect(s.body.errors).toEqual([expect.objectContaining({ pointer: '/payload' })]);
  });

  it('TC-ET-073: a lone surrogate in a payload string is malformed_request at its pointer', async () => {
    const p = await publish(g, a, undefined, {
      raw: `{"draft":${JSON.stringify(draft())},"payload":{"a":"\\ud800"}}`,
    });
    await refusedWith(p, 400, 'malformed_request');
    expect(p.body.errors).toEqual([expect.objectContaining({ pointer: '/payload/a' })]);
  });
});

describe('steps 7 to 9: forwarded context, depth, and authority', () => {
  it('TC-ET-090: an envelope sealed in E2 is invalid_inbound_context in E', async () => {
    const e2 = await ingest(db, { environment: E2, keys: g.keys });
    try {
      const a2 = await agentWith(e2, PUBLISHER, { env: E2 });
      await e2.listen();
      const s2 = await subscribe(e2, await agentWith(e2, SUBSCRIBER, { env: E2 }));
      expect((await publish(e2, a2)).status).toBe(202);
      await flush(e2);
      await s2.until(() => s2.events.length === 1);
      const d = s2.deliveries()[0]!;
      s2.destroy();
      const b = await agentWith(g, [...PUBLISHER, ...SUBSCRIBER]);
      const r = await publish(
        g,
        b,
        {},
        {
          draft: draft({ inbound: { envelope: d.envelope, seal: d.seal } }),
        },
      );
      await refusedWith(r, 400, 'invalid_inbound_context');
      expect(r.body.errors).toBeUndefined();
    } finally {
      await e2.close();
    }
  });

  it('TC-ET-019: a forwarded chain at 32 is chain_too_deep', async () => {
    const b = await agentWith(g, PUBLISHER);
    const env = {
      envelopeVersion: 1,
      scope: { ...E },
      originMode: 'autonomous',
      actorChain: Array.from({ length: 32 }, (_, i) => ({ agent: `x${i}`, instance: 'i' })),
      traceContext: { traceparent: TRACEPARENT },
    };
    const r = await publish(g, b, {}, { draft: draft({ inbound: sealed(env) }) });
    await refusedWith(r, 400, 'chain_too_deep');
  });

  it('TC-ET-009: no autonomy declared: forbidden at publish and subscribe, no record', async () => {
    const c = await agentWith(g, [...PUBLISHER, ...SUBSCRIBER], { autonomy: false });
    await refusedWith(await publish(g, c), 403, 'forbidden');
    await refusedWith(await subscribeRefused(g, c), 403, 'forbidden');
    expect(await records(g, c.agent)).toEqual([]);
  });

  it('TC-ET-010 and 011: a missing permission is forbidden, with no record', async () => {
    const b = await agentWith(g, SUBSCRIBER);
    const a = await agentWith(g, PUBLISHER);
    await refusedWith(await publish(g, b), 403, 'forbidden');
    await refusedWith(await subscribeRefused(g, a), 403, 'forbidden');
    expect(await records(g, a.agent)).toEqual([]);
    expect(await records(g, b.agent)).toEqual([]);
    expect(g.runtime.streams.size).toBe(1);
  });

  it('TC-ET-044: a forwarding hop never gains beyond the intersection', async () => {
    // C holds event:subscribe only; D holds publish and subscribe; D forwards C's envelope.
    const c = await agentWith(g, SUBSCRIBER);
    const d = await agentWith(g, [...PUBLISHER, ...SUBSCRIBER]);
    const env = {
      envelopeVersion: 1,
      scope: { ...E },
      originMode: 'autonomous',
      actorChain: [{ agent: c.agent, instance: c.instance }],
      traceContext: { traceparent: TRACEPARENT },
    };
    const r = await publish(g, d, {}, { draft: draft({ inbound: sealed(env) }) });
    await refusedWith(r, 403, 'forbidden');
  });
});

describe('step 1: the route limits (TC-ET-050, 051, 052)', () => {
  it('TC-ET-050: each limit is accepted to step 2; one byte over is payload_too_large', async () => {
    for (const [url, limit] of [
      [PUBLISH, 262_144],
      [SUBSCRIBE, 65_536],
    ] as const) {
      const at = 'x'.repeat(limit);
      const r1 = await send(g.edge, url, { body: at });
      expect(r1.status, `${url} at the limit`).toBe(401);
      const r2 = await send(g.edge, url, { body: at + 'x' });
      expect(r2.status, `${url} over the limit`).toBe(413);
      expect(r2.body.code).toBe('payload_too_large');
    }
    // Any other path keeps 16 KiB: refused before it is found to be unknown.
    const other = await send(g.edge, '/other', { body: 'x'.repeat(16 * 1024 + 1) });
    expect(other.status).toBe(413);
  });

  it('TC-ET-051: the guaranteed maximum-size forwarding draft passes step 1 of both', async () => {
    const env = maxEnvelope();
    const forward = {
      clientContractVersion: '0.1.0',
      traceContext: { traceparent: TRACEPARENT, tracestate: maxTracestate() },
      inbound: { envelope: env, seal: 's'.repeat(1024) },
    };
    const indented = (v: unknown): string => escapeNonAscii(JSON.stringify(v, null, 2));
    const sub = indented({ draft: forward });
    const pub = indented({ draft: forward, payload: { p: 'é'.repeat(65_536 / 2 - 4) } });
    expect(Buffer.byteLength(sub)).toBeLessThanOrEqual(65_536);
    expect(Buffer.byteLength(pub)).toBeLessThanOrEqual(262_144);
    const a = await agentWith(g, PUBLISHER);
    const b = await agentWith(g, SUBSCRIBER);
    // Past step 1: refused later (the seal), never payload_too_large.
    expect((await publish(g, a, undefined, { raw: pub })).status).toBe(400);
    expect((await subscribeRefused(g, b, { raw: sub })).status).toBe(400);
    const grow = (text: string, limit: number): string =>
      text.replace(/\n}$/, `${' '.repeat(limit - Buffer.byteLength(text) + 1)}\n}`);
    expect((await publish(g, a, undefined, { raw: grow(pub, 262_144) })).status).toBe(413);
    expect((await subscribeRefused(g, b, { raw: grow(sub, 65_536) })).status).toBe(413);
  });

  it('TC-ET-052: maximum nesting at each limit gives a deterministic Problem', async () => {
    const a = await agentWith(g, PUBLISHER);
    const b = await agentWith(g, SUBSCRIBER);
    const nest = (limit: number, around: (deep: string) => string): string => {
      const shell = Buffer.byteLength(around(''));
      const depth = Math.floor((limit - shell) / 2);
      return around(`${'['.repeat(depth)}${']'.repeat(depth)}`);
    };
    // Publish: the payload nested to 256 KiB; jcs's walk measures it, over P.
    const pub = nest(262_144, (deep) => `{"draft":${JSON.stringify(draft())},"payload":${deep}}`);
    // Subscribe: a forwarded envelope's unknown field nested to 64 KiB; U3's walks bound it.
    const env = JSON.stringify({
      envelopeVersion: 1,
      scope: { ...E },
      originMode: 'autonomous',
      actorChain: [{ agent: 'a', instance: 'i' }],
      traceContext: { traceparent: TRACEPARENT },
      'x-deep': 0,
    });
    const sub = nest(65_536, (deep) =>
      `{"draft":${JSON.stringify(draft({ inbound: { envelope: '@', seal: 'v1.k1.x' } }))}}`.replace(
        '"@"',
        env.replace('0}', `${deep}}`),
      ),
    );
    for (const [raw, limit] of [
      [pub, 262_144],
      [sub, 65_536],
    ] as const)
      expect(Buffer.byteLength(raw)).toBeLessThanOrEqual(limit);
    const p = await publish(g, a, undefined, { raw: pub });
    await refusedWith(p, 413, 'payload_too_large');
    const s = await subscribeRefused(g, b, { raw: sub });
    await refusedWith(s, 400, 'invalid_inbound_context');
  });
});

/**
 * A publish carrying two Authorization headers, over a real connection. The
 * headers are a raw array, so Node's client adds no Host; it is sent here, or
 * Node's server would answer 400 to an HTTP/1.1 request without one.
 */
function twoCredentials(token: string): Promise<{ status: number; code: unknown }> {
  const body = JSON.stringify({ draft: draft(), payload: 1 });
  return new Promise((resolve, reject) => {
    const req = httpRequest(
      `${g.url()}${PUBLISH}`,
      {
        method: 'POST',
        // Raw header pairs: Authorization twice.
        headers: [
          'host',
          new URL(g.url()).host,
          'content-type',
          'application/json',
          'content-length',
          String(Buffer.byteLength(body)),
          'authorization',
          `Bearer ${token}`,
          'authorization',
          `Bearer ${token}`,
        ],
      },
      (res) => {
        let text = '';
        res.setEncoding('utf8');
        res.on('data', (d: string) => (text += d));
        res.on('end', () =>
          resolve({
            status: res.statusCode ?? 0,
            code: (JSON.parse(text) as { code?: unknown }).code,
          }),
        );
      },
    );
    req.on('error', reject);
    req.end(body);
  });
}

/** NFR-ET-04's envelope: 32 entries, defined fields, one flat unknown field to 16 384 bytes. */
function maxEnvelope(): Record<string, unknown> {
  const env: Record<string, unknown> = {
    envelopeVersion: 1,
    scope: { organization: 'o'.repeat(63), project: 'p'.repeat(63), environment: 'e'.repeat(63) },
    originMode: 'autonomous',
    actorChain: Array.from({ length: 32 }, (_, i) => ({
      agent: `agent-${i}`.padEnd(63, 'a'),
      instance: `inst-${i}`.padEnd(63, 'i'),
    })),
    reBroadening: [{ hop: 31, permissions: ['event:publish'] }],
    traceContext: { traceparent: TRACEPARENT, tracestate: maxTracestate() },
  };
  const base = canonicalize({ ...env, 'x-pad': '' }).bytes.length;
  // Non-ASCII padding: escaped as \uXXXX it is the worst case for the indented form.
  const chars = Math.floor((16_384 - base) / 2);
  return { ...env, 'x-pad': 'é'.repeat(chars) };
}

function maxTracestate(): string {
  return Array.from({ length: 32 }, (_, i) => `k${i}=${'v'.repeat(10)}`)
    .join(',')
    .slice(0, 512);
}

function escapeNonAscii(text: string): string {
  return text.replace(/[\u0080-￿]/g, (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`);
}

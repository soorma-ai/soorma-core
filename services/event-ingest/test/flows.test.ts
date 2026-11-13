// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S4's flows in process, over a real stream: TC-ET-026, 034, 037, 049, 058,
// 071, 072, 076, 079, 080, 092; the publish and subscribe records (BR-AT-ET);
// a forward through a real Delivery (US-09's shape, TC-ET-005's in-process
// half).
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import {
  agentWith,
  draft,
  flush,
  ingest,
  publish,
  PUBLISHER,
  records,
  subscribe,
  SUBSCRIBER,
  SPONSOR,
  E,
  sameJson,
  SseClient,
  type Ingest,
} from './support.ts';
import { parseRawNumbers } from '@soorma/jcs';

let db: TestEnvDatabase;
let g: Ingest;

beforeAll(async () => {
  db = await testEnvDatabase();
  g = await ingest(db);
  await g.listen();
});
afterAll(async () => {
  await g?.close();
  await db?.drop();
});

describe('TC-ET-079: a stream’s headers, and its deliveries in order', () => {
  it('200 text/event-stream, no-store, the Soorma headers; three deliveries in the order accepted', async () => {
    const a = await agentWith(g, PUBLISHER);
    const b = await agentWith(g, SUBSCRIBER);
    const stream = await subscribe(g, b);
    expect(stream.status).toBe(200);
    expect(stream.headers['content-type']).toBe('text/event-stream; charset=utf-8');
    expect(stream.headers['cache-control']).toBe('no-store');
    expect(stream.headers['soorma-contract-version']).toBe('0.1.0');
    expect(stream.headers['soorma-request-id']).toMatch(/^[0-9a-f-]{36}$/);
    for (const n of [1, 2, 3]) expect((await publish(g, a, { n })).status).toBe(202);
    await flush(g);
    await stream.until(() => stream.deliveries().length === 3);
    expect(stream.deliveries().map((d) => d.payload)).toEqual([{ n: 1 }, { n: 2 }, { n: 3 }]);
    stream.destroy();
  });
});

describe('TC-ET-092: neither operation returns its own hop’s envelope', () => {
  it('publish is 202 with no body; the stream carries only delivery events', async () => {
    const a = await agentWith(g, PUBLISHER);
    const b = await agentWith(g, SUBSCRIBER);
    const stream = await subscribe(g, b);
    const r = await publish(g, a);
    expect(r.status).toBe(202);
    expect(r.text).toBe('');
    expect(r.headers['soorma-request-id']).toBeDefined();
    await flush(g);
    await stream.until(() => stream.events.length === 1);
    expect(stream.events.map((e) => e.event)).toEqual(['delivery']);
    const delivery = stream.deliveries()[0]!;
    // The Delivery is A's: B's own subscribe envelope enters none.
    expect(delivery.envelope.actorChain).toEqual([{ agent: a.agent, instance: a.instance }]);
    stream.destroy();
  });
});

describe('TC-ET-058: the stream’s encoding', () => {
  it('event, one data line of compact JSON, a blank line; no id or retry; Last-Event-ID changes nothing', async () => {
    const a = await agentWith(g, PUBLISHER);
    const b = await agentWith(g, SUBSCRIBER);
    const stream = await subscribe(g, b, { headers: { 'last-event-id': '42' } });
    expect(stream.status).toBe(200);
    await publish(g, a, { text: 'line one\nline two' });
    await flush(g);
    await stream.until(() => stream.events.length === 1);
    const wire = stream.raw.join('');
    expect(wire).toMatch(/^event: delivery\ndata: \{[^\n]*\}\n\n$/);
    expect(wire).toContain('line one\\nline two');
    expect(wire).not.toMatch(/^id:/m);
    expect(wire).not.toMatch(/^retry:/m);
    stream.destroy();
  });
});

describe('TC-ET-080: one frame per publish, the same for every stream', () => {
  it('three subscribers receive byte-identical frames', async () => {
    const a = await agentWith(g, PUBLISHER);
    const streams = await Promise.all(
      [1, 2, 3].map(async () => subscribe(g, await agentWith(g, SUBSCRIBER))),
    );
    await publish(g, a, { same: true });
    await flush(g);
    for (const s of streams) await s.until(() => s.events.length === 1);
    const frames = streams.map((s) => s.raw.join(''));
    expect(new Set(frames).size).toBe(1);
    for (const s of streams) s.destroy();
  });
});

describe('NP-ET-05: payload numbers delivered exactly as written', () => {
  it('TC-ET-071: an integer above 2^53', async () => {
    const a = await agentWith(g, PUBLISHER);
    const stream = await subscribe(g, await agentWith(g, SUBSCRIBER));
    const raw = `{"draft":${JSON.stringify(draft())},"payload":{"id":12345678901234567890}}`;
    expect((await publish(g, a, undefined, { raw })).status).toBe(202);
    await flush(g);
    await stream.until(() => stream.events.length === 1);
    expect(stream.events[0]!.data).toContain('"payload":{"id":12345678901234567890}');
    stream.destroy();
  });

  it('TC-ET-072: a long decimal and exponent forms, -0 included', async () => {
    const a = await agentWith(g, PUBLISHER);
    const stream = await subscribe(g, await agentWith(g, SUBSCRIBER));
    const raw = `{"draft":${JSON.stringify(draft())},"payload":[0.10000000000000000555, 6.02214076e23, 1E+400, -0]}`;
    expect((await publish(g, a, undefined, { raw })).status).toBe(202);
    await flush(g);
    await stream.until(() => stream.events.length === 1);
    expect(stream.events[0]!.data).toContain(
      '"payload":[0.10000000000000000555,6.02214076e23,1E+400,-0]',
    );
    stream.destroy();
  });

  it('TC-ET-076: duplicate member names keep the last value', async () => {
    const a = await agentWith(g, PUBLISHER);
    const stream = await subscribe(g, await agentWith(g, SUBSCRIBER));
    const raw = `{"draft":${JSON.stringify(draft())},"payload":{"k":1,"k":2}}`;
    expect((await publish(g, a, undefined, { raw })).status).toBe(202);
    await flush(g);
    await stream.until(() => stream.events.length === 1);
    expect(stream.events[0]!.data).toContain('"payload":{"k":2}');
    stream.destroy();
  });

  it('TC-ET-049: the bound at its edge, with a large number making up most of it', async () => {
    const a = await agentWith(g, PUBLISHER);
    const stream = await subscribe(g, await agentWith(g, SUBSCRIBER));
    // [ + digits + ] is 65 536 bytes in JCS: exactly P.
    const digits = '9'.repeat(65_536 - 2);
    const at = `{"draft":${JSON.stringify(draft())},"payload":[${digits}]}`;
    const over = `{"draft":${JSON.stringify(draft())},"payload":[${digits}9]}`;
    expect((await publish(g, a, undefined, { raw: at })).status).toBe(202);
    const refused = await publish(g, a, undefined, { raw: over });
    expect(refused.status).toBe(413);
    expect(refused.body).toMatchObject({
      code: 'payload_too_large',
      errors: [{ pointer: '/payload' }],
    });
    await flush(g);
    await stream.until(() => stream.events.length === 1);
    expect(stream.events[0]!.data).toContain(`"payload":[${digits}]`);
    stream.destroy();
  });
});

describe('BR-AT-ET: one record per publish and per subscribe', () => {
  it('TC-ET-034: a record alone recovers scope, actor, chain, origin, and sponsor', async () => {
    const a = await agentWith(g, PUBLISHER);
    const b = await agentWith(g, SUBSCRIBER);
    const stream = await subscribe(g, b);
    await publish(g, a);
    await flush(g);
    await stream.until(() => stream.events.length === 1);
    stream.destroy();
    const [pub] = await records(g, a.agent);
    expect(pub).toMatchObject({
      organization: E.organization,
      project: E.project,
      environment: E.environment,
      operation: 'publish',
      actor_kind: 'agent',
      registration: a.agent,
      instance: a.instance,
      sponsor: SPONSOR,
      credential_kind: 'agentCredential',
      credential_id: a.cid,
      origin: { originMode: 'autonomous' },
      rebroadening_load_bearing: false,
      rebroadening_hop: null,
    });
    expect(pub!.chain).toEqual([{ agent: a.agent, instance: a.instance }]);
    const [sub] = await records(g, b.agent);
    expect(sub).toMatchObject({ operation: 'subscribe', registration: b.agent, sponsor: SPONSOR });
  });

  it('TC-ET-026: a forward that is not load-bearing records no hop', async () => {
    const a = await agentWith(g, PUBLISHER);
    const b = await agentWith(g, [...SUBSCRIBER, ...PUBLISHER]);
    const stream = await subscribe(g, b);
    await publish(g, a);
    await flush(g);
    await stream.until(() => stream.events.length === 1);
    const delivered = stream.deliveries()[0]!;
    // B forwards A's envelope: A holds event:publish, so nothing re-broadens.
    const forward = draft({ inbound: { envelope: delivered.envelope, seal: delivered.seal } });
    expect((await publish(g, b, { next: 1 }, { draft: forward })).status).toBe(202);
    await flush(g);
    await stream.until(() => stream.events.length === 2);
    stream.destroy();
    const [rec] = (await records(g, b.agent)).filter((r) => r.operation === 'publish');
    expect(rec!.chain).toEqual([
      { agent: a.agent, instance: a.instance },
      { agent: b.agent, instance: b.instance },
    ]);
    expect(rec).toMatchObject({ rebroadening_load_bearing: false, rebroadening_hop: null });
  });

  it('a load-bearing forward records the presenter’s hop (BR-AT-ET-03)', async () => {
    const a = await agentWith(g, PUBLISHER);
    // B declares event:subscribe for re-broadening: A's set lacks it.
    const b = await agentWith(g, SUBSCRIBER, { declaration: SUBSCRIBER });
    const watcher = await subscribe(g, await agentWith(g, SUBSCRIBER));
    await publish(g, a);
    await flush(g);
    await watcher.until(() => watcher.events.length === 1);
    const d = watcher.deliveries()[0]!;
    const stream = await subscribe(g, b, {
      draft: draft({ inbound: { envelope: d.envelope, seal: d.seal } }),
    });
    expect(stream.status).toBe(200);
    const [rec] = await records(g, b.agent);
    expect(rec).toMatchObject({
      operation: 'subscribe',
      rebroadening_load_bearing: true,
      rebroadening_hop: 1,
      origin: { originMode: 'autonomous' },
    });
    expect(rec!.chain).toHaveLength(2);
    stream.destroy();
    watcher.destroy();
  });

  it('TC-ET-037: a publish leaves its record and nothing of the event', async () => {
    const a = await agentWith(g, PUBLISHER);
    const marker = `marker-${Date.now()}`;
    expect((await publish(g, a, { marker })).status).toBe(202);
    const su = await db.superuser();
    try {
      const { rows } = await su.query<{ t: string }>(
        `SELECT table_name AS t FROM information_schema.tables WHERE table_schema = 'public'`,
      );
      for (const { t } of rows) {
        const hit = await su.query(
          `SELECT 1 FROM ${JSON.stringify(t)} AS r WHERE r::text LIKE $1`,
          [`%${marker}%`],
        );
        expect(hit.rowCount, t).toBe(0);
      }
    } finally {
      await su.end();
    }
    expect((await records(g, a.agent)).map((r) => r.operation as string)).toEqual(['publish']);
  });
});

describe('TC-ET-052 (NFR-ET-05) through the whole publish path', () => {
  // The deepest payloads within P (64 KiB on JCS), each with a number at the
  // bottom: accepted, recorded, and written to the stream; the delivered
  // payload equals the published one, compared by walking (D-CG-ET-29).
  const cases: [string, string][] = [
    ['arrays', `${'['.repeat(32_767)}7${']'.repeat(32_767)}`],
    ['objects', `${'{"a":'.repeat(10_921)}1E400${'}'.repeat(10_921)}`],
  ];
  it.each(cases)('%s nested to P: 202, the record, the Delivery', async (_name, payload) => {
    expect(Buffer.byteLength(payload)).toBeLessThanOrEqual(65_536);
    const a = await agentWith(g, PUBLISHER);
    const stream = await subscribe(g, await agentWith(g, SUBSCRIBER));
    const raw = `{"draft":${JSON.stringify(draft())},"payload":${payload}}`;
    const r = await publish(g, a, undefined, { raw });
    expect({ status: r.status, code: r.body?.code }).toEqual({ status: 202, code: undefined });
    expect((await records(g, a.agent)).map((x) => x.operation as string)).toEqual(['publish']);
    await flush(g);
    await stream.until(() => stream.events.length === 1);
    const data = stream.events[0]!.data;
    expect(() => JSON.parse(data) as unknown).not.toThrow();
    const delivered = (parseRawNumbers(data) as { payload: unknown }).payload;
    expect(sameJson(delivered, parseRawNumbers(payload))).toBe(true);
    stream.destroy();
  });
});

describe('D-CG-ET-29: the payload arrives in RFC 8785 order', () => {
  it('a payload with members out of order arrives sorted by name, values equal', async () => {
    const a = await agentWith(g, PUBLISHER);
    const stream = await subscribe(g, await agentWith(g, SUBSCRIBER));
    const sent = '{"b":1,"a":{"d":2.50,"c":[3,{"z":0,"y":1E2}]},"2":"two","10":-0}';
    const raw = `{"draft":${JSON.stringify(draft())},"payload":${sent}}`;
    expect((await publish(g, a, undefined, { raw })).status).toBe(202);
    await flush(g);
    await stream.until(() => stream.events.length === 1);
    const data = stream.events[0]!.data;
    expect(data).toContain(
      '"payload":{"10":-0,"2":"two","a":{"c":[3,{"y":1E2,"z":0}],"d":2.50},"b":1}}',
    );
    expect(
      sameJson((parseRawNumbers(data) as { payload: unknown }).payload, parseRawNumbers(sent)),
    ).toBe(true);
    stream.destroy();
  });
});

describe('every Delivery frame', () => {
  it('parses with JSON.parse, on every stream this file opened', () => {
    let frames = 0;
    for (const client of SseClient.all)
      for (const e of client.events)
        if (e.event === 'delivery') {
          frames += 1;
          expect(() => JSON.parse(e.data) as unknown).not.toThrow();
        }
    expect(frames).toBeGreaterThan(10);
  });
});

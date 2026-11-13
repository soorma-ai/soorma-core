// SPDX-License-Identifier: FSL-1.1-ALv2
//
// U7 on the local stack, by raw calls (D-ET-34; NP-ET-18). Done when 3, 4, 6,
// 7 are U5's journey's (agent-registration.test.ts), from its real agents;
// these cases seed their own agents as the store's owner and take each
// instance's credential from that environment's S3:
//
//  TC-ET-005 (a triggered subscribe re-broadens at B's hop), 009 (no autonomy),
//  015 and 039 (nothing crosses environments), 018 (live only), 020 (a
//  forwarded origin propagates), 023 (unknown fields survive), 037 (nothing of
//  the event is stored), 040 (every refusal holds for a raw call), 041 (the
//  same credential from inside network e), 048 (two instances of one name),
//  071 and 072 (numbers as written), 090 (an envelope sealed in E2), and 014,
//  017, 028, 031 (revocation reaches a publish and an open stream within the
//  bound, at either granularity: one wait of B plus R).
//
// Run by `pnpm test:e2e` on a fresh stack; skipped otherwise.
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { assertProblem } from '../packages/perimeter/testing/index.ts';
import { seedAgentRevocation, seedCredentialRevocation, sql } from './agent-credentials-support.ts';
import {
  deliveries,
  draft,
  ended,
  forwarding,
  ingestRecords,
  instanceOf,
  publishAt,
  publishRaw,
  records,
  sealAs,
  seedAgent,
  seededInstance,
  subscribeAt,
  type EventStream,
  type Instance,
  type Reply,
} from './event-transport-support.ts';
import { code, E2E, json, SECRETS } from './support.ts';

const RUN = Date.now().toString(36);
const name = (role: string): string => `et-${role}-${RUN}`;
const PUB = ['event:publish'];
const SUB = ['event:subscribe'];
const BOTH = [...PUB, ...SUB];
const pause = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms));

/** The shared Problem assertion, on a raw reply. */
function problemIs(r: Reply, status: number, problem: string): void {
  assertProblem({ status: r.status, headers: r.headers, body: json(r) }, { status, code: problem });
}

/** A stream that must stay silent: its events now, compared after `ms`. */
async function silent(stream: EventStream, act: () => Promise<unknown>, ms = 1000): Promise<void> {
  const before = stream.events.length;
  await act();
  await pause(ms);
  expect(stream.events.length).toBe(before);
}

describe.skipIf(!E2E)('U7 event-transport on the local stack', () => {
  let a: Instance;
  let watcher: Instance;
  let watch: EventStream;

  it('set-up: A publishes, a watcher subscribes (seeded, each bootstrapped at S3)', async () => {
    a = await seededInstance('e', name('a'), { standing: PUB });
    watcher = await seededInstance('e', name('w'), { standing: SUB });
    watch = await subscribeAt('e', watcher.token);
    expect(watch.status).toBe(200);
  });

  it('TC-ET-071, 072: payload numbers are delivered exactly as written', async () => {
    const big = `{"draft":${JSON.stringify(draft())},"payload":{"id":12345678901234567890}}`;
    const spelled = `{"draft":${JSON.stringify(draft())},"payload":[0.10000000000000000555, 6.02214076e23, 1E+400, -0]}`;
    for (const text of [big, spelled])
      expect((await publishRaw('e', a.token, text)).status).toBe(202);
    expect(await watch.until(() => deliveries(watch).length >= 2)).toBe(true);
    const raw = deliveries(watch).map((d) => d.raw);
    expect(raw.some((t) => t.endsWith('"payload":{"id":12345678901234567890}}'))).toBe(true);
    expect(
      raw.some((t) => t.endsWith('"payload":[0.10000000000000000555,6.02214076e23,1E+400,-0]}')),
    ).toBe(true);
  });

  it('TC-ET-018: a subscriber offline at publish time never receives the event', async () => {
    const late = await seededInstance('e', name('late'), { standing: SUB });
    expect((await publishAt('e', a.token, { before: 'late' })).status).toBe(202);
    const stream = await subscribeAt('e', late.token);
    // A Last-Event-ID header changes nothing: the stream is not resumable.
    expect(stream.status).toBe(200);
    expect((await publishAt('e', a.token, { after: 'late' })).status).toBe(202);
    expect(await stream.until(() => deliveries(stream).length >= 1)).toBe(true);
    await pause(500);
    expect(deliveries(stream).map((d) => d.payload)).toEqual([{ after: 'late' }]);
    stream.close();
  });

  it('TC-ET-005, 020, 023: forwarding A’s envelope, at B’s hop, and its unknown fields', async () => {
    expect((await publishAt('e', a.token, { step: 'origin' })).status).toBe(202);
    expect(await watch.until(() => deliveries(watch).some((d) => isStep(d, 'origin')))).toBe(true);
    const origin = deliveries(watch).find((d) => isStep(d, 'origin'))!;

    // TC-ET-005: B holds event:subscribe and declares it for re-broadening; A
    // does not hold it, so it is load-bearing at B's hop. B is not given that envelope.
    const b = await seededInstance('e', name('b'), { standing: SUB, declaration: SUB });
    const bs = await subscribeAt('e', b.token, forwarding(origin));
    expect(bs.status).toBe(200);
    bs.close();
    const [sub] = records('e', b.agent, 'subscribe');
    expect(sub).toMatchObject({
      chain: [
        { agent: a.agent, instance: a.instance },
        { agent: b.agent, instance: b.instance },
      ],
      origin: { originMode: 'autonomous' },
      rebroadening_load_bearing: true,
      rebroadening_hop: 1,
    });

    // TC-ET-020: C holds publish and subscribe, and forwards A's envelope.
    const c = await seededInstance('e', name('c'), { standing: BOTH });
    expect((await publishAt('e', c.token, { step: 'forwarded' }, forwarding(origin))).status).toBe(
      202,
    );
    expect(await watch.until(() => deliveries(watch).some((d) => isStep(d, 'forwarded')))).toBe(
      true,
    );
    const fwd = deliveries(watch).find((d) => isStep(d, 'forwarded'))!;
    expect(fwd.envelope.actorChain).toEqual([
      { agent: a.agent, instance: a.instance },
      { agent: c.agent, instance: c.instance },
    ]);
    expect(fwd.envelope.originMode).toBe('autonomous');

    // TC-ET-023: an unknown field at the envelope's top level and within, sealed with E's key.
    const future = {
      ...origin.envelope,
      'x-future': { kept: true },
      scope: { ...origin.envelope.scope, 'x-scope': 1 },
    };
    const r = await publishAt(
      'e',
      c.token,
      { step: 'future' },
      {
        ...draft(),
        inbound: { envelope: future, seal: sealAs('e', future) },
      },
    );
    expect(r.status, r.body).toBe(202);
    expect(await watch.until(() => deliveries(watch).some((d) => isStep(d, 'future')))).toBe(true);
    const kept = deliveries(watch).find((d) => isStep(d, 'future'))!;
    expect(kept.envelope['x-future']).toEqual({ kept: true });
    expect(kept.envelope.scope['x-scope']).toBe(1);
  });

  it('TC-ET-048: two instances asserting one name each hold their own stream', async () => {
    const secret = seedAgent('e', name('twin'), { standing: SUB });
    const one = await instanceOf('e', name('twin'), secret, 'same');
    const two = await instanceOf('e', name('twin'), secret, 'same');
    const s1 = await subscribeAt('e', one.token);
    const s2 = await subscribeAt('e', two.token);
    expect((await publishAt('e', a.token, { step: 'twins' })).status).toBe(202);
    for (const s of [s1, s2])
      expect(await s.until(() => deliveries(s).some((d) => isStep(d, 'twins')))).toBe(true);
    expect([ended(s1), ended(s2)]).toEqual([undefined, undefined]);
    s1.close();
    s2.close();
  });

  it('TC-ET-009: no autonomy declared: forbidden at publish and subscribe, no record', async () => {
    const c = await seededInstance('e', name('noauto'), { standing: BOTH, autonomy: false });
    problemIs(await publishAt('e', c.token, { x: 1 }), 403, 'forbidden');
    const s = await subscribeAt('e', c.token);
    expect(s.status).toBe(403);
    s.close();
    expect(ingestRecords('e', c.agent)).toEqual([]);
  });

  it('TC-ET-015, 039: nothing crosses environments; each store holds only its own records', async () => {
    const a2 = await seededInstance('e2', name('a2'), { standing: PUB });
    const w2 = await seededInstance('e2', name('w2'), { standing: SUB });
    const s2 = await subscribeAt('e2', w2.token);
    expect(s2.status).toBe(200);
    expect((await publishAt('e', a.token, { step: 'only-e' })).status).toBe(202);
    expect((await publishAt('e2', a2.token, { step: 'only-e2' })).status).toBe(202);
    expect(await s2.until(() => deliveries(s2).some((d) => isStep(d, 'only-e2')))).toBe(true);
    expect(await watch.until(() => deliveries(watch).some((d) => isStep(d, 'only-e')))).toBe(true);
    await pause(5000);
    expect(deliveries(s2).every((d) => !isStep(d, 'only-e'))).toBe(true);
    expect(deliveries(watch).every((d) => !isStep(d, 'only-e2'))).toBe(true);
    expect(deliveries(s2).every((d) => d.envelope.scope.environment === 'e2')).toBe(true);
    expect(records('e', a2.agent)).toEqual([]);
    expect(records('e2', a.agent)).toEqual([]);
    s2.close();
  });

  it('TC-ET-090: an envelope sealed in E2 is invalid_inbound_context in E', async () => {
    const a2 = await seededInstance('e2', name('a2s'), { standing: PUB });
    const w2 = await seededInstance('e2', name('w2s'), { standing: SUB });
    const s2 = await subscribeAt('e2', w2.token);
    expect((await publishAt('e2', a2.token, { step: 'sealed-e2' })).status).toBe(202);
    expect(await s2.until(() => deliveries(s2).some((d) => isStep(d, 'sealed-e2')))).toBe(true);
    const e2Delivery = deliveries(s2).find((d) => isStep(d, 'sealed-e2'))!;
    s2.close();
    const c = await seededInstance('e', name('c90'), { standing: BOTH });
    await silent(watch, async () => {
      const r = await publishAt('e', c.token, { x: 1 }, forwarding(e2Delivery));
      problemIs(r, 400, 'invalid_inbound_context');
    });
  });

  it('TC-ET-037: a publish leaves its record and nothing of the event', async () => {
    const marker = `et-marker-${RUN}`;
    const p = await seededInstance('e', name('p37'), { standing: PUB });
    expect((await publishAt('e', p.token, { marker })).status).toBe(202);
    expect(await watch.until(() => deliveries(watch).some((d) => d.raw.includes(marker)))).toBe(
      true,
    );
    const { seal } = deliveries(watch).find((d) => d.raw.includes(marker))!;
    const tables = sql(
      'e',
      "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';",
    ).split('\n');
    for (const t of tables) {
      for (const needle of [marker, seal])
        expect(
          sql('e', `SELECT count(*) FROM "${t}" r WHERE r::text LIKE '%${needle}%';`),
          `${t}`,
        ).toBe('0');
    }
    expect(ingestRecords('e', p.agent).map((r) => r.operation)).toEqual(['publish']);
  });

  it('TC-ET-040: every refusal holds for a raw call, each a Problem', async () => {
    const b = await seededInstance('e', name('b40'), { standing: SUB });
    const forty = name('a40');
    const a40 = await seededInstance('e', forty, { standing: PUB });
    const deep = {
      envelopeVersion: 1,
      scope: { organization: 'o1', project: 'p1', environment: 'e' },
      originMode: 'autonomous',
      actorChain: Array.from({ length: 32 }, (_, i) => ({ agent: `x${i}`, instance: 'i' })),
      traceContext: draft().traceContext,
    };
    await silent(watch, async () => {
      const cases: [Promise<Reply>, number, string][] = [
        [publishAt('e', 'soorma_ec_AAAA.BBBB.CCCC', { x: 1 }), 401, 'credential_refused'],
        [publishAt('e', 'soorma_si_AAAA.BBBB.CCCC', { x: 1 }), 401, 'credential_refused'],
        [publishAt('e', 'soorma_ac_not.a.token', { x: 1 }), 401, 'credential_refused'],
        [publishAt('e', b.token, { x: 1 }), 403, 'forbidden'],
        [publishAt('e', a40.token, { x: 1 }, { ...draft(), scope: {} }), 400, 'stamped_field_set'],
        [
          publishAt('e', a40.token, { x: 1 }, { ...draft(), originMode: 'autonomous' }),
          400,
          'stamped_field_set',
        ],
        [publishAt('e', a40.token, { x: 1 }, { ...draft(), topic: 't' }), 400, 'unknown_field'],
        [
          publishAt('e', a40.token, { x: 1 }, { ...draft(), clientContractVersion: '9.9.9' }),
          400,
          'unsupported_contract_version',
        ],
        [
          publishAt(
            'e',
            a40.token,
            { x: 1 },
            { ...draft(), inbound: { envelope: deep, seal: sealAs('e', deep) } },
          ),
          400,
          'chain_too_deep',
        ],
        [
          publishRaw('e', a40.token, `{"draft":${JSON.stringify(draft())}}`),
          400,
          'malformed_request',
        ],
        [
          publishRaw('e', a40.token, `{"draft":${JSON.stringify(draft())},"payload":1,"extra":1}`),
          400,
          'unknown_field',
        ],
        [
          publishRaw(
            'e',
            a40.token,
            `{"draft":${JSON.stringify(draft())},"payload":{"a":"\\ud800"}}`,
          ),
          400,
          'malformed_request',
        ],
        [
          publishRaw(
            'e',
            a40.token,
            `{"draft":${JSON.stringify(draft())},"payload":["${'x'.repeat(65_536)}"]}`,
          ),
          413,
          'payload_too_large',
        ],
        [publishRaw('e', a40.token, 'x'.repeat(262_145)), 413, 'payload_too_large'],
      ];
      for (const [reply, status, problem] of cases) problemIs(await reply, status, problem);
    });
    // A subscribe without event:subscribe opens no stream (TC-ET-011's shape).
    const s = await subscribeAt('e', a40.token);
    expect(s.status).toBe(403);
    s.close();
    expect(ingestRecords('e', forty)).toEqual([]);
  });

  it('TC-ET-041: the same credential from inside network e is the same agent', async () => {
    const p = await seededInstance('e', name('p41'), { standing: PUB });
    expect((await publishAt('e', p.token, { from: 'host' })).status).toBe(202);
    const script = `
      const https = require('node:https');
      const fs = require('node:fs');
      const token = fs.readFileSync(0, 'utf8').trim();
      const body = JSON.stringify({ draft: ${JSON.stringify(draft())}, payload: { from: 'network-e' } });
      const call = (auth) => new Promise((done) => {
        const req = https.request({ host: 'event-ingest.e.soorma.internal', port: 8443, path: '/events', method: 'POST',
          ca: fs.readFileSync('/ca.pem'), headers: { 'content-type': 'application/json', 'soorma-contract-version': '0.1.0',
          'content-length': Buffer.byteLength(body), ...(auth ? { authorization: 'Bearer ' + token } : {}) } },
          (res) => { res.resume(); res.on('end', () => done(res.statusCode)); });
        req.on('error', () => done(-1));
        req.end(body);
      });
      (async () => { console.log(await call(true), await call(false)); })();`;
    const out = execFileSync(
      'docker',
      [
        'run',
        '--rm',
        '-i',
        '--network',
        'soorma-local_e',
        '-v',
        `${join(SECRETS, 'stack-ca.pem')}:/ca.pem:ro`,
        'node:26.13.0@sha256:6d2c7d5d074bf72f81ddc252b4fbb5d625bc028eeda49cb4b8c2ff8eda1ee617',
        'node',
        '-e',
        script,
      ],
      { input: p.token, encoding: 'utf8' },
    ).trim();
    expect(out).toBe('202 401');
    const pubs = records('e', p.agent, 'publish');
    expect(pubs).toHaveLength(2);
    expect(
      new Set(pubs.map((r) => `${r.registration}|${r.instance}|${r.credential_id}`)).size,
    ).toBe(1);
  });

  it('TC-ET-014, 017, TC-ET-028, 031: revocation reaches a publish and an open stream within B, at either granularity', async () => {
    const byCid = await seededInstance('e', name('rc'), { standing: BOTH });
    const byAgent = await seededInstance('e', name('ra'), { standing: BOTH });
    const streams = [await subscribeAt('e', byCid.token), await subscribeAt('e', byAgent.token)];
    for (const s of streams) expect(s.status).toBe(200);
    seedCredentialRevocation('e', byCid.cid);
    seedAgentRevocation('e', byAgent.agent);
    const revokedAt = Date.now();
    // Within B, a cached not_revoked may still serve; past B plus R, both are refused.
    for (const s of streams) expect(await s.until(() => ended(s) !== undefined, 75_000)).toBe(true);
    const endedWithin = Date.now() - revokedAt;
    expect(endedWithin).toBeLessThanOrEqual(61_000 + 5_000);
    for (const s of streams) expect(ended(s)).toEqual({ code: 'credential_refused' });
    const r1 = await publishAt('e', byCid.token, { x: 1 });
    const r2 = await publishAt('e', byAgent.token, { x: 1 });
    problemIs(r1, 401, 'credential_refused');
    problemIs(r2, 401, 'credential_refused');
    // TC-ET-031: byte-identical apart from the request id.
    const same = (r: Reply): string => r.body.replace(/urn:soorma:request:[0-9a-f-]+/, '*');
    expect(same(r1)).toBe(same(r2));
    expect(code(r1)).toBe('credential_refused');
  }, 120_000);

  it('closes the watcher', () => {
    watch.close();
    expect(readFileSync(join(SECRETS, 'stack-ca.pem')).length).toBeGreaterThan(0);
  });
});

function isStep(d: { payload: unknown }, step: string): boolean {
  return (d.payload as { step?: unknown } | null)?.step === step;
}

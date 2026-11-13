// SPDX-License-Identifier: Apache-2.0
// S4 event-ingest's operations in the contract (U7 event-transport):
// TC-ET-024, 038, 045, 053; Functional Design §14; NFR-ET-02, 03, 06.
// TC-ET-053's other half, P's value equal to S4's constant, is S4's own test.
import { describe, expect, it } from 'vitest';
import { parse } from 'yaml';
import { contractFindings } from '../scripts/checks/rules.ts';
import {
  compatFindings,
  loadFixtures,
  parseClassifications,
  readChangelog,
} from '../scripts/checks/compat.ts';
import { contract, contractFile, convention, fixture, valid, validator } from './helpers.ts';

type Json = Record<string, any>;

const doc = parse(contractFile('event-ingest.openapi.yaml')) as Json;
const others = ['org-gateway', 'control-gateway', 'data-gateway'].map(
  (s) => parse(contractFile(`${s}.openapi.yaml`)) as Json,
);
const envelope = convention('envelope.md');
const errors = convention('errors.md');
const errorsText = contractFile('conventions/errors.md');
const preRelease = convention('pre-release.md');
const changelog = contractFile('CHANGELOG.md');
const VERSION_PARAM =
  'conventions/components.openapi.yaml#/components/parameters/SoormaContractVersion';
const SHARED = 'conventions/components.openapi.yaml#/components/schemas/';

const PUBLISH = '/events';
const SUBSCRIBE = '/subscriptions';
const op = (path: string): Json => doc.paths[path].post as Json;
const response = (o: Json, status: string): Json => {
  const r = o.responses[status] as Json;
  return typeof r.$ref === 'string'
    ? (doc.components.responses[r.$ref.split('/').pop()!] as Json)
    : r;
};
const operationIds = (d: Json): string[] =>
  Object.values(d.paths as Json).flatMap((item) =>
    Object.values(item as Json).map((o) => (o as Json).operationId as string),
  );
const draft = fixture('draft/valid/sample');

describe('TC-ET-024: S4 operations are defined in the contract and validated against it', () => {
  it('holds exactly publish and subscribe, each a POST', () => {
    expect(Object.keys(doc.paths as Json).sort()).toEqual([PUBLISH, SUBSCRIBE]);
    for (const path of [PUBLISH, SUBSCRIBE])
      expect(Object.keys(doc.paths[path] as Json)).toEqual(['post']);
    expect(op(PUBLISH).operationId).toBe('publish');
    expect(op(SUBSCRIBE).operationId).toBe('subscribe');
  });

  it('both name agentCredential only, and take the version parameter', () => {
    expect(doc.security).toBeUndefined();
    for (const path of [PUBLISH, SUBSCRIBE]) {
      expect(op(path).security).toEqual([{ agentCredential: [] }]);
      expect(op(path).parameters).toEqual([{ $ref: VERSION_PARAM }]);
    }
    expect(doc.components.securitySchemes).toEqual({
      agentCredential: {
        $ref: 'conventions/components.openapi.yaml#/components/securitySchemes/agentCredential',
      },
    });
  });

  it('the bodies: publish { draft, payload }, subscribe { draft }, closed, the draft by reference', () => {
    const body = (path: string, name: string): void =>
      expect(op(path).requestBody).toEqual({
        required: true,
        content: { 'application/json': { schema: { $ref: `#/components/schemas/${name}` } } },
      });
    body(PUBLISH, 'PublishRequest');
    body(SUBSCRIBE, 'SubscribeRequest');
    const publish = doc.components.schemas.PublishRequest as Json;
    const subscribe = doc.components.schemas.SubscribeRequest as Json;
    for (const s of [publish, subscribe]) {
      expect(s.additionalProperties).toBe(false);
      expect(s.properties.draft).toEqual({ $ref: `${SHARED}Draft` });
    }
    expect([...(publish.required as string[])].sort()).toEqual(['draft', 'payload']);
    expect(Object.keys(publish.properties as Json).sort()).toEqual(['draft', 'payload']);
    expect(Object.keys(publish.properties.payload as Json)).toEqual(['description']);
    expect(subscribe.required).toEqual(['draft']);
    expect(Object.keys(subscribe.properties as Json)).toEqual(['draft']);
  });

  it('publish answers 202 with no body; subscribe 200 text/event-stream, its events named', () => {
    const accepted = op(PUBLISH).responses['202'] as Json;
    expect(accepted.content).toBeUndefined();
    const ok = op(SUBSCRIBE).responses['200'] as Json;
    expect(Object.keys(ok.content as Json)).toEqual(['text/event-stream']);
    expect(Object.keys(ok.headers as Json)).toContain('Cache-Control');
    expect(ok.content['text/event-stream']['x-soorma-events']).toEqual({
      delivery: { $ref: `${SHARED}Delivery` },
      end: { $ref: '#/components/schemas/StreamEnd' },
    });
    const end = doc.components.schemas.StreamEnd as Json;
    expect(end.additionalProperties).toBe(true);
    expect(end.required).toEqual(['code']);
    expect(doc.components.schemas.StreamEndCode.anyOf).toEqual([
      {
        enum: ['credential_expired', 'credential_refused', 'unavailable', 'superseded', 'overflow'],
      },
      { type: 'string' },
    ]);
  });

  it('statuses: no 429 at S4 (its throttle is unavailable)', () => {
    for (const path of [PUBLISH, SUBSCRIBE]) {
      const ok = path === PUBLISH ? '202' : '200';
      expect(Object.keys(op(path).responses as Json).sort()).toEqual(
        [ok, '400', '401', '403', '413', '500', '503'].sort(),
      );
    }
  });

  it('every response carries the Soorma headers; 401 alone WWW-Authenticate; 503 Retry-After', () => {
    for (const path of [PUBLISH, SUBSCRIBE]) {
      const o = op(path);
      for (const status of Object.keys(o.responses as Json)) {
        const headers = Object.keys((response(o, status).headers ?? {}) as Json);
        expect(headers, `${path} ${status}`).toEqual(
          expect.arrayContaining(['Soorma-Contract-Version', 'Soorma-Request-Id']),
        );
        if (status === '401') expect(headers).toContain('WWW-Authenticate');
        else expect(headers).not.toContain('WWW-Authenticate');
        if (status === '503') expect(headers).toContain('Retry-After');
      }
    }
  });

  it('a body violating the schema is refused by the validator', () => {
    expect(valid('event-ingest#PublishRequest', { draft, payload: { k: 'v' } })).toBe(true);
    expect(valid('event-ingest#PublishRequest', { draft, payload: null })).toBe(true);
    expect(valid('event-ingest#SubscribeRequest', { draft })).toBe(true);
    for (const body of [
      { draft },
      { payload: {} },
      { draft, payload: {}, topic: 't' },
      { draft: { ...draft, scope: {} }, payload: {} },
      { draft: '0.1.0', payload: {} },
    ])
      expect(valid('event-ingest#PublishRequest', body), JSON.stringify(body)).toBe(false);
    for (const body of [{}, { draft, payload: {} }, { draft: { ...draft, topic: 't' } }])
      expect(valid('event-ingest#SubscribeRequest', body), JSON.stringify(body)).toBe(false);
  });

  it('has valid and invalid fixtures for each definition, and each validates as expected', () => {
    const fixtures = loadFixtures();
    for (const name of ['PublishRequest', 'SubscribeRequest', 'StreamEnd', 'StreamEndCode']) {
      const of = fixtures.filter((f) => f.schema === `event-ingest#${name}`);
      expect(
        of.some((f) => f.expectedValid),
        name,
      ).toBe(true);
      expect(
        of.some((f) => !f.expectedValid),
        name,
      ).toBe(true);
      for (const f of of) expect(valid(f.schema, f.data), f.path).toBe(f.expectedValid);
    }
  });
});

describe('TC-ET-038: S4’s document holds data-face operations only (I6)', () => {
  it('exactly publish and subscribe, accepting only the agent credential', () => {
    expect(operationIds(doc).sort()).toEqual(['publish', 'subscribe']);
    const schemes = JSON.stringify(doc.paths);
    expect(schemes).not.toContain('environmentCredential');
    expect(schemes).not.toContain('signIn');
  });

  it('no other surface document holds an S4 operation or path', () => {
    for (const other of others) {
      const ids = operationIds(other);
      expect(ids).not.toContain('publish');
      expect(ids).not.toContain('subscribe');
      for (const path of Object.keys(other.paths as Json)) {
        expect(path.startsWith('/events')).toBe(false);
        expect(path.startsWith('/subscriptions')).toBe(false);
      }
    }
  });
});

describe('TC-ET-045: the completed contract passes U1’s checks, and every change is classified', () => {
  it('the structural checks and the compatibility check find nothing', () => {
    expect(contractFindings(contract)).toEqual([]);
    const classifications = parseClassifications(readChangelog());
    expect(compatFindings(loadFixtures(), validator.validate, classifications)).toEqual([]);
  });

  it('payload_too_large is in the shared contract, widened to a publish’s payload', () => {
    const row = errorsText.split('\n').find((l) => l.startsWith('| `payload_too_large`'))!;
    expect(row).toMatch(/\| 413 /);
    expect(row).toContain('The body exceeds the published size bound');
    expect(row).toContain("a publish's `payload` exceeds the Delivery payload bound");
    expect(row).toContain(
      "None; for a publish's `payload` over the Delivery payload bound, `errors[]` with one entry: the `pointer` `/payload`",
    );
  });

  it('CHANGELOG.md records the surface and each statement, each compatible', () => {
    const section = changelog.slice(changelog.indexOf('### Added by U7 `event-transport`'));
    expect(section.length).toBeGreaterThan(0);
    for (const name of [
      'event-ingest.openapi.yaml',
      '`publish`',
      '`subscribe`',
      'payload_too_large',
      'The Delivery',
      'The stream',
      'pre-release.md',
    ])
      expect(section).toContain(name);
    for (const classification of [
      'Compatible: new operations',
      'Compatible: a clarification',
      "Compatible: an open code's scope widened, its meaning kept",
      'Compatible: a value the conventions left to U7',
      'Compatible: a statement',
    ])
      expect(section).toContain(classification);
  });

  it('the envelope-bearing table is unchanged, and states the draft’s place on S4', () => {
    expect(envelope).toMatch(/\| Publish \| S4 \| A draft in the request \|/);
    expect(envelope).toContain('On S4, the draft is the `draft` member of the request body');
    const order = errors.slice(errors.indexOf('## Check order'));
    expect(order).toContain('On S4, where the draft is the body');
    expect(order).toContain(
      'a `draft` missing or not an object is `malformed_request` with the pointer `/draft`',
    );
    expect(order).toContain('On S4, the body');
    expect(order).toContain('Then, for a publish, the Delivery payload bound: `payload_too_large`');
  });
});

describe('TC-ET-053: the contract’s statements on payloads and streams', () => {
  it.each([
    'The Delivery payload bound is set by the event transport unit (U7) and published there: 64 KiB (65 536 bytes)',
    'measured on the payload',
    'with each number counted by its source text',
    'Payload numbers are delivered exactly as written',
    'I-JSON numbers are not required',
    'Payload strings must be well-formed Unicode',
    'Duplicate member names keep the last value',
    'Object members are delivered in RFC 8785 order (sorted by name), not the order sent',
    'publish 256 KiB (262 144 bytes), subscribe 64 KiB (65 536 bytes)',
    "Clients should serialize drafts and payloads compact, without HTML-safe or other ASCII escaping (for example Go's `json.Encoder.SetEscapeHTML(false)`)",
    'Exactly one `end` event',
    'The codes are an open set',
    '`superseded`',
    '`overflow`',
    'Heartbeats are comment lines',
    'At most one stream is open per credential lineage',
    'A stream is not resumable',
    'a `Last-Event-ID` header is ignored',
    'A stream ends at its credential',
  ])('envelope.md states: %s', (statement) => {
    expect(envelope).toContain(statement);
  });

  it('pre-release.md states the bound, and no resumption, beside the unspecified semantics', () => {
    expect(preRelease).toContain('The Delivery payload bound is 64 KiB (65 536 bytes)');
    expect(preRelease).not.toContain('not set in this version');
    expect(preRelease).toContain('Event delivery semantics are unspecified at this version');
    expect(preRelease).toContain('A stream is not resumable');
  });

  it('every stream end code in the document is named in envelope.md', () => {
    const codes = (doc.components.schemas.StreamEndCode.anyOf[0] as { enum: string[] }).enum;
    for (const code of codes) expect(envelope).toContain(`\`${code}\``);
  });
});

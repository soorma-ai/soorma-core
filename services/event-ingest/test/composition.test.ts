// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S4's composition and its boundaries: TC-ET-030 (one bound, one constant,
// no configuration key), TC-ET-033 (the environment from configuration only),
// TC-ET-043 (S4 imports only the allowlisted names of P2 and P3), TC-ET-047
// (the payload is never read beyond its bound and well-formedness), TC-ET-075
// (the start-up self-check, no fallback), TC-ET-083's manifest half (the
// production closure), TC-ET-091 (humanGrants grants nothing).
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createCachingAgentFacts } from '@soorma/authority';
import { ConfigurationError } from '@soorma/config';
import { createRevocationCache, PROPAGATION_BOUND_MS } from '@soorma/credentials';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import { checkRawJson } from '../src/raw-json-check.ts';
import { humanGrants, type CacheFactories } from '../src/runtime.ts';
import * as settings from '../src/settings.ts';
import { agentWith, ingest, publish, PUBLISHER, revokeCredential, type Ingest } from './support.ts';

const ROOT = join(import.meta.dirname, '../../..');
const SRC = join(import.meta.dirname, '../src');

const sources = (): { file: string; text: string }[] =>
  readdirSync(SRC, { recursive: true, encoding: 'utf8' })
    .filter((f) => f.endsWith('.ts'))
    .map((f) => ({ file: f, text: readFileSync(join(SRC, f), 'utf8') }));

let db: TestEnvDatabase;
const open: Ingest[] = [];
beforeAll(async () => {
  db = await testEnvDatabase();
});
afterEach(async () => {
  for (const g of open.splice(0)) await g.close();
});
afterAll(async () => {
  await db?.drop();
});

describe('TC-ET-030: one bound, one constant, no configuration key', () => {
  it('both caches receive ttl === PROPAGATION_BOUND_MS; the answer is re-read at exactly 60 s', async () => {
    const seen: { factory: string; ttl: number }[] = [];
    const factories: CacheFactories = {
      createRevocationCache: (source, options) => {
        seen.push({ factory: 'revocation', ttl: options.ttl });
        return createRevocationCache(source, options);
      },
      createCachingAgentFacts: (source, options) => {
        seen.push({ factory: 'facts', ttl: options.ttl });
        return createCachingAgentFacts(source, options);
      },
    };
    const g = await ingest(db, { factories });
    open.push(g);
    expect(seen).toEqual([
      { factory: 'revocation', ttl: PROPAGATION_BOUND_MS },
      { factory: 'facts', ttl: PROPAGATION_BOUND_MS },
    ]);
    expect(PROPAGATION_BOUND_MS).toBe(60_000);
    const a = await agentWith(g, PUBLISHER);
    expect((await publish(g, a)).status).toBe(202);
    await revokeCredential(g, a);
    g.clock.ms += 59_999;
    expect((await publish(g, a)).status).toBe(202);
    g.clock.ms += 1;
    expect((await publish(g, a)).status).toBe(401);
  });

  it('no key for a bound, TTL, or propagation interval: in the tenancy schema, P9’s S4 part, or S4', () => {
    // S4's part of the schema names no bound at all; nowhere does a key name a
    // TTL or a propagation interval. (S3's part has 'bound': its bootstrap
    // bound's counter secret, an abuse bound, not this one.)
    const schema = JSON.parse(
      readFileSync(join(ROOT, 'packages/config/schema/tenancy.schema.json'), 'utf8'),
    ) as { $defs: Record<string, unknown> };
    const keysOf = (node: unknown): string[] => {
      const out: string[] = [];
      const pending = [node];
      while (pending.length > 0) {
        const n = pending.pop();
        if (Array.isArray(n)) pending.push(...(n as unknown[]));
        else if (typeof n === 'object' && n !== null)
          for (const [k, v] of Object.entries(n)) {
            out.push(k);
            pending.push(v);
          }
      }
      return out;
    };
    expect(schema.$defs.EventIngest).toBeDefined();
    expect(
      keysOf(schema.$defs.EventIngest).filter((k) => /bound|ttl|propagation/i.test(k)),
    ).toEqual([]);
    expect(keysOf(schema).filter((k) => /ttl|propagation/i.test(k))).toEqual([]);
    expect(Object.keys(settings).filter((k) => /bound|ttl|propagation/i.test(k))).toEqual([
      'DELIVERY_PAYLOAD_BOUND',
    ]);
    // PROPAGATION_BOUND_MS is imported where the caches are built, never defined in S4.
    for (const { file, text } of sources())
      expect(text, file).not.toMatch(/PROPAGATION_BOUND_MS\s*=/);
    expect(readFileSync(join(SRC, 'runtime.ts'), 'utf8')).toMatch(
      /import \{[^}]*\bPROPAGATION_BOUND_MS\b[^}]*\} from '@soorma\/credentials'/,
    );
  });
});

describe('TC-ET-033: S4 learns its environment from configuration only', () => {
  it('no source reads a request, a header, or the token for the environment it serves', () => {
    for (const { file, text } of sources()) {
      expect(text, file).not.toMatch(/process\.env\.SOORMA_(ORGANIZATION|PROJECT_ID)/);
      expect(text, file).not.toMatch(/headers\[['"](x-)?soorma-environment/i);
    }
    const main = readFileSync(join(SRC, 'main.ts'), 'utf8');
    expect(main).toContain('loadEventIngest(');
    expect(main).toContain('organization: settings.organization');
  });
});

describe('TC-ET-043: S4 imports only the allowlisted names of P2 and P3', () => {
  const ALLOWED = new Set([
    'createEnvelopeAdmission',
    'createCachingAgentFacts',
    'loadSealKeyRing',
  ]);

  it('nothing from @soorma/envelope; from @soorma/authority only the allowlist and types', () => {
    for (const { file, text } of sources()) {
      expect(text, file).not.toContain("'@soorma/envelope'");
      for (const m of text.matchAll(
        /import\s+(type\s+)?\{([^}]*)\}\s+from\s+'@soorma\/authority'/g,
      )) {
        if (m[1]) continue;
        for (const raw of m[2]!.split(',')) {
          const name = raw.trim();
          if (name === '' || name.startsWith('type ')) continue;
          expect(ALLOWED.has(name), `${file}: ${name}`).toBe(true);
        }
      }
      expect(text, file).not.toMatch(/import\s+\*\s+as\s+\w+\s+from\s+'@soorma\/authority'/);
    }
  });

  it('the built output holds the same imports, when built', () => {
    const dist = join(import.meta.dirname, '../dist');
    if (!existsSync(dist)) return;
    for (const f of readdirSync(dist, { recursive: true, encoding: 'utf8' }).filter((x) =>
      x.endsWith('.js'),
    )) {
      const text = readFileSync(join(dist, f), 'utf8');
      expect(text, f).not.toContain("'@soorma/envelope'");
    }
  });
});

describe('TC-ET-047: the payload is never read beyond its bound and well-formedness', () => {
  it('the payload is parsed, measured by jcs, and serialized; no member of it is read', () => {
    const edge = readFileSync(join(SRC, 'edge/edge-handlers.ts'), 'utf8');
    // No member of the payload is read: never payload.x or payload[...].
    expect(edge).not.toMatch(/\bpayload\.\w/);
    expect(edge).not.toMatch(/\bpayload\[/);
    expect(edge).toContain("canonicalize(value, { numbers: 'source' })");
    // The frame (D-CG-ET-29): the payload written by jcs, never read.
    expect(edge).toContain('`"payload":${canonicalize(payload, { numbers: \'source\' }).text}}`');
  });
});

describe('TC-ET-075: S4 refuses to start without JSON.rawJSON', () => {
  it('a runtime without it is a ConfigurationError; this runtime passes', () => {
    expect(() => checkRawJson()).not.toThrow();
    const json = JSON as unknown as Record<string, unknown>;
    const saved = json.rawJSON;
    try {
      delete json.rawJSON;
      expect(() => checkRawJson()).toThrow(ConfigurationError);
    } finally {
      json.rawJSON = saved;
    }
    expect(() => checkRawJson()).not.toThrow();
  });

  it('start() runs the check before reading any configuration', () => {
    const main = readFileSync(join(SRC, 'main.ts'), 'utf8');
    const body = main.slice(main.indexOf('export async function start('));
    expect(body.indexOf('checkRawJson();')).toBeGreaterThan(-1);
    expect(body.indexOf('checkRawJson();')).toBeLessThan(body.indexOf('loadEventIngest('));
  });
});

describe('TC-ET-091: humanGrants grants nothing at S4', () => {
  it('the empty set, for any principal', async () => {
    for (const principal of [
      { kind: 'human' as const, principal: 'h@example.com' },
      { kind: 'agent' as const, agent: 'a' },
    ])
      expect([
        ...(await humanGrants.grantsOf(principal, {
          organization: 'o1',
          project: 'p1',
          environment: 'e',
        })),
      ]).toEqual([]);
  });
});

describe('TC-ET-083 (manifest half): S4 never links the organization level', () => {
  function manifests(): Map<string, string[]> {
    const out = new Map<string, string[]>();
    for (const base of ['packages', 'seams', 'services'])
      for (const name of readdirSync(join(ROOT, base))) {
        const path = join(ROOT, base, name, 'package.json');
        if (!existsSync(path)) continue;
        const j = JSON.parse(readFileSync(path, 'utf8')) as {
          name: string;
          dependencies?: Record<string, string>;
        };
        out.set(j.name, Object.keys(j.dependencies ?? {}));
      }
    return out;
  }

  function closure(start: string): Set<string> {
    const all = manifests();
    const seen = new Set<string>();
    const pending = [start];
    while (pending.length > 0)
      for (const d of all.get(pending.pop()!) ?? [])
        if (d.startsWith('@soorma/') && !seen.has(d)) {
          seen.add(d);
          pending.push(d);
        }
    return seen;
  }

  it('the closure reaches the entry point and P5, and never P10, P6, or P8', () => {
    const s4 = closure('@soorma/event-ingest');
    for (const p of [
      '@soorma/authority',
      '@soorma/credentials',
      '@soorma/attribution',
      '@soorma/jcs',
    ])
      expect(s4).toContain(p);
    for (const p of [
      '@soorma/org-identity',
      '@soorma/identity-resolution',
      '@soorma/identity-resolution-seam',
      '@soorma/agent-identity',
      '@soorma/abuse-bound',
    ])
      expect(s4).not.toContain(p);
  });

  it('no source names the organization level or a signing key', () => {
    for (const { file, text } of sources()) {
      expect(text, file).not.toContain('@soorma/org-identity');
      expect(text, file).not.toContain('mintAgentCredential');
      expect(text, file).not.toContain('loadEnvironmentKeyRing');
    }
  });
});

describe('TC-ET-053 (S4’s half): the published values are S4’s constants', () => {
  const envelopeMd = readFileSync(join(ROOT, 'contract/conventions/envelope.md'), 'utf8')
    .replace(/\*\*/g, '')
    .replace(/\s+/g, ' ');
  const bytes = (n: number): string => n.toLocaleString('en-US').replace(/,/g, ' ');

  it('P, and the two body limits, as envelope.md states them', () => {
    expect(settings.DELIVERY_PAYLOAD_BOUND).toBe(64 * 1024);
    expect(envelopeMd).toContain(
      `published there: 64 KiB (${bytes(settings.DELIVERY_PAYLOAD_BOUND)} bytes)`,
    );
    expect(envelopeMd).toContain(
      `publish 256 KiB (${bytes(settings.PUBLISH_BODY_LIMIT)} bytes), subscribe 64 KiB (${bytes(settings.SUBSCRIBE_BODY_LIMIT)} bytes)`,
    );
    expect(settings.ROUTE_BODY_LIMITS).toEqual({
      '/events': settings.PUBLISH_BODY_LIMIT,
      '/subscriptions': settings.SUBSCRIBE_BODY_LIMIT,
    });
  });

  it('the heartbeat, and the end codes S4 writes, as the contract states them', () => {
    expect(settings.HEARTBEAT_MS).toBe(15_000);
    expect(envelopeMd).toContain('at least every 15 seconds without another event');
  });
});

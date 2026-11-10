// SPDX-License-Identifier: FSL-1.1-ALv2
// TC-AE-039: the entry point's structure: one import, no framework, refusals
// returned, the security log, the validator compiled once, no new
// dependency. TC-AE-036 step 3: canonical JSON computed once per envelope.
// D-AE-04, 10, 23, 26; NP-05, NP-08; NFR-AE-03, 05, 20, 22, 23; L1-12, 13,
// 34, 36; I2.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as envelopeModule from '@soorma/envelope';
import * as jcs from '@soorma/jcs';
import { describe, expect, it, vi } from 'vitest';
import { admissionE, draft, envelope, padTo, request, sealed } from './support.ts';

vi.mock('@soorma/jcs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@soorma/jcs')>();
  return { ...actual, canonicalize: vi.fn(actual.canonicalize) };
});
vi.mock('@soorma/envelope', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@soorma/envelope')>();
  return { ...actual, createDraftValidator: vi.fn(actual.createDraftValidator) };
});

const repo = fileURLToPath(new URL('../../../', import.meta.url));
const PUB = { standing: ['event:publish'] };

function sources(dir: string): string[] {
  const out: string[] = [];
  const walk = (d: string): void => {
    for (const name of readdirSync(d)) {
      const path = join(d, name);
      if (statSync(path).isDirectory()) walk(path);
      else if (name.endsWith('.ts')) out.push(path);
    }
  };
  walk(join(repo, dir));
  return out;
}

const read = (path: string): string => readFileSync(path, 'utf8');
const imports = (path: string): string[] =>
  [...read(path).matchAll(/from\s+'([^']+)'/g)].map((m) => m[1]!);

describe('TC-AE-039: the entry point’s structure', () => {
  it('1: none of the five imports NestJS; no service imports P2; P3 imports neither P1 nor P11', () => {
    for (const pkg of [
      'packages/jcs',
      'packages/envelope',
      'packages/authority',
      'packages/policy-decision',
      'seams/policy-decision',
    ])
      for (const file of sources(`${pkg}/src`))
        expect(imports(file).filter((i) => i.startsWith('@nestjs/'))).toEqual([]);
    for (const service of readdirSync(join(repo, 'services')))
      for (const file of sources(`services/${service}/src`))
        expect(imports(file)).not.toContain('@soorma/envelope');
    const p3 = sources('packages/authority/src').flatMap(imports);
    expect(p3).not.toContain('@soorma/perimeter');
    expect(p3).not.toContain('@soorma/policy-decision');
    const manifest = JSON.parse(read(join(repo, 'packages/authority/package.json'))) as {
      dependencies: Record<string, string>;
    };
    expect(Object.keys(manifest.dependencies).sort()).toEqual([
      '@soorma/envelope',
      '@soorma/policy-decision-seam',
    ]);
  });

  it('2, 4: one refusal at each of steps 5 to 10, each returned and logged once, with exactly six fields', async () => {
    const chain = Array.from({ length: 32 }, (_, i) => `a${i}`);
    const { admission, log } = admissionE({ b: PUB, c: { autonomy: false, ...PUB }, a: PUB });
    const cases = [
      request('b', [], { requestId: 's5' }),
      request('b', draft({ scope: {} }), { requestId: 's6' }),
      request('b', draft({ inbound: { envelope: envelope(['a']), seal: 'v1.k1.x' } }), {
        requestId: 's7',
      }),
      request('b', draft({ inbound: sealed(envelope(chain)) }), { requestId: 's8' }),
      request('c', draft(), { requestId: 's9' }),
      request('b', draft({ inbound: sealed(padTo(envelope(['a']), 16380)) }), { requestId: 's10' }),
    ];
    for (const r of cases) {
      const result = await admission.admit(r);
      expect('refused' in result).toBe(true);
    }
    expect(log.events.map((e) => [e.requestId, e.code])).toEqual([
      ['s5', 'malformed_request'],
      ['s6', 'stamped_field_set'],
      ['s7', 'invalid_inbound_context'],
      ['s8', 'chain_too_deep'],
      ['s9', 'forbidden'],
      ['s10', 'envelope_too_large'],
    ]);
    for (const event of log.events) {
      expect(Object.keys(event).sort()).toEqual([
        'agent',
        'code',
        'environment',
        'instance',
        'reason',
        'requestId',
      ]);
      const text = JSON.stringify(event);
      expect(text).not.toContain('v1.k1');
      expect(text).not.toContain('00-4bf92f3577b34da6a3ce929d0e0e4736');
      expect(text).not.toContain('actorChain');
    }
  });

  it('3: a scope other than the configured one, and an empty required set: internal_error', async () => {
    const { admission, log } = admissionE({ b: PUB });
    expect(
      await admission.admit(
        request('b', draft(), { scope: { organization: 'o1', project: 'p1', environment: 'e2' } }),
      ),
    ).toEqual({
      refused: { code: 'internal_error' },
    });
    expect(await admission.admit(request('b', draft(), { required: [] }))).toEqual({
      refused: { code: 'internal_error' },
    });
    expect(log.events.map((e) => e.reason)).toEqual([
      'credential_scope_mismatch',
      'empty_required_set',
    ]);
  });

  it('5: the draft validator is compiled once, when the entry point is built (NFR-AE-03)', async () => {
    const created = vi.mocked(envelopeModule.createDraftValidator);
    created.mockClear();
    const { admission } = admissionE({ b: PUB });
    for (let i = 0; i < 100; i++)
      await admission.admit(request('b', i % 2 ? draft() : draft({ foo: i })));
    expect(created).toHaveBeenCalledTimes(1);
  });

  it('7: no new direct dependency: Ajv’s row gains packages/envelope as runtime (NFR-AE-23)', () => {
    const register = read(join(repo, 'DEPENDENCIES.md'));
    const ajv = register.split('\n').find((l) => l.startsWith('| `ajv`'))!;
    expect(ajv).toContain('`packages/envelope`');
    expect(ajv).toMatch(/runtime \([^)]*`packages\/envelope`/);
    for (const pkg of [
      'packages/jcs',
      'packages/envelope',
      'packages/authority',
      'packages/policy-decision',
      'seams/policy-decision',
    ]) {
      const manifest = JSON.parse(read(join(repo, pkg, 'package.json'))) as {
        dependencies?: Record<string, string>;
        devDependencies?: Record<string, string>;
      };
      const external = Object.keys({
        ...manifest.dependencies,
        ...manifest.devDependencies,
      }).filter((d) => !d.startsWith('@soorma/'));
      for (const dep of external) expect(register).toContain(`| \`${dep}\``);
    }
  });
});

describe('TC-AE-036 step 3: canonical JSON is computed once per envelope (NFR-AE-05)', () => {
  it('exactly two calls for a forwarding admit: inbound.envelope, then the stamped envelope', async () => {
    const { admission } = admissionE({ a: PUB, b: PUB });
    const inbound = sealed(envelope(['a']));
    const canonicalize = vi.mocked(jcs.canonicalize);
    canonicalize.mockClear();
    const result = await admission.admit(request('b', draft({ inbound })));
    expect('admitted' in result).toBe(true);
    expect(canonicalize).toHaveBeenCalledTimes(2);
    expect(canonicalize.mock.calls[0]![0]).toBe(inbound.envelope);
  });
});

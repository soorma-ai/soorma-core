// SPDX-License-Identifier: FSL-1.1-ALv2
// The sql, compare, inject, and secrets checks: on the real tree, and on
// mutated copies. TC-OI-057 (the secret patterns), TC-OI-061's neighbours;
// D-CG-OI-03, 04, 05; NFR-OI-17, 29.
import { execFileSync } from 'node:child_process';
import { generateKeyPairSync, randomBytes } from 'node:crypto';
import {
  createReadStream,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { codeFindings, sourceProjects } from '../checks/code.ts';
import { repositoryFindings, tarFindings, textFindings } from '../checks/secrets.ts';
import { repoRoot } from '../checks/workspace.ts';

const dirs: string[] = [];
afterAll(() => {
  for (const d of dirs) rmSync(d, { recursive: true, force: true });
});

/** A throwaway tree with one package: its tsconfig, the brand types, and the given sources. */
function tree(sources: Record<string, string>): string {
  const root = mkdtempSync(join(tmpdir(), 'soorma-code-'));
  dirs.push(root);
  const pkg = join(root, 'packages', 'x');
  mkdirSync(join(pkg, 'src'), { recursive: true });
  writeFileSync(
    join(pkg, 'tsconfig.json'),
    JSON.stringify({
      extends: join(repoRoot, 'tsconfig.base.json'),
      compilerOptions: { experimentalDecorators: true, types: [], lib: ['es2024'] },
      include: ['src/**/*.ts'],
    }),
  );
  writeFileSync(
    join(pkg, 'src', 'brands.ts'),
    `declare const secretBytesBrand: unique symbol;
declare const verifierBrand: unique symbol;
declare const totpCodeBrand: unique symbol;
declare const statementBrand: unique symbol;
export type SecretBytes = Uint8Array & { readonly [secretBytesBrand]: true };
export type Verifier = string & { readonly [verifierBrand]: true };
export type TotpCode = string & { readonly [totpCodeBrand]: true };
export type Statement = string & { readonly [statementBrand]: true };
export const statement = (t: string): Statement => t as Statement;
export const query = { query: (_s: Statement, _p?: unknown[]): void => undefined };
export const raw = { query: (_s: string): void => undefined };
export function Injectable(): ClassDecorator { return () => undefined; }
export function Controller(): ClassDecorator { return () => undefined; }
export function Inject(_t: symbol): ParameterDecorator { return () => undefined; }
`,
  );
  for (const [name, text] of Object.entries(sources)) writeFileSync(join(pkg, 'src', name), text);
  return root;
}

describe('the code checks on the real tree', () => {
  it.each(['sql', 'compare', 'inject'] as const)(
    '%s passes',
    (check) => {
      expect(codeFindings(check)).toEqual([]);
    },
    120_000,
  );
});

describe('compare (D-CG-OI-05): type-based, not by name', () => {
  it('fails on a Verifier, a SecretBytes, and a union containing TotpCode; passes ordinary values', () => {
    const root = tree({
      'a.ts': `import type { SecretBytes, TotpCode, Verifier } from './brands.ts';
export function f(v: Verifier, w: Verifier, b: SecretBytes, c: SecretBytes, t: TotpCode | undefined,
  statusCode: number, problem: { code: string }): boolean[] {
  return [v === w, b !== c, t === undefined, statusCode === 204, problem.code === 'secret_rejected'];
}
`,
    });
    const lines = codeFindings('compare', root).map((f) => f.location);
    expect(lines).toHaveLength(3);
    expect(lines.every((l) => l.endsWith('a.ts:4'))).toBe(true);
  });
});

describe('sql (D-CG-OI-04)', () => {
  it('fails on a query with other SQL, statement() outside sql.ts, and a substitution in sql.ts', () => {
    const root = tree({
      'sql.ts': `import { statement } from './brands.ts';
const table = 'x';
export const SQL = { ok: statement('SELECT 1'), bad: statement(\`SELECT * FROM \${table}\`) };
`,
      'a.ts': `import { query, raw, statement } from './brands.ts';
import { SQL } from './sql.ts';
query.query(SQL.ok);
raw.query('DELETE FROM principals');
query.query(statement('SELECT 2'));
`,
    });
    const found = codeFindings('sql', root).map(
      (f) => `${f.location.split('/').pop()} ${f.message}`,
    );
    expect(found).toEqual(
      expect.arrayContaining([
        expect.stringMatching(/^sql\.ts:3 a template literal/),
        expect.stringMatching(/^a\.ts:4 query\(\) takes a statement/),
        expect.stringMatching(/^a\.ts:5 statement\(\) is called only/),
      ]),
    );
    expect(found).toHaveLength(3);
  });
});

describe('inject (D-CG-OI-03)', () => {
  it('fails on an injected class’s constructor parameter without @Inject', () => {
    const root = tree({
      'a.ts': `import { Controller, Inject, Injectable } from './brands.ts';
const T = Symbol('t');
@Injectable()
export class Good { constructor(@Inject(T) x: unknown) { void x; } }
@Controller()
export class Bad { constructor(x: unknown) { void x; } }
export class Plain { constructor(x: unknown) { void x; } }
`,
    });
    const found = codeFindings('inject', root);
    expect(found).toHaveLength(1);
    expect(found[0]!.message).toContain('Bad');
  });
});

describe('secrets (TC-OI-057)', () => {
  const key = generateKeyPairSync('ed25519').privateKey.export({ format: 'pem', type: 'pkcs8' });
  const material = `soorma_em_${randomBytes(32).toString('base64url')}`;

  it('finds real-shaped material, tokens, and keys; ignores placeholders and PEM-parsing code', () => {
    expect(textFindings('f', material)).toHaveLength(1);
    expect(textFindings('f', String(key))).toHaveLength(1);
    expect(
      textFindings('f', `soorma_si_${'a'.repeat(20)}.${'b'.repeat(40)}.${'c'.repeat(86)}`),
    ).toHaveLength(1);
    expect(
      textFindings('f', "const x = 'soorma_em_x'; const t = 'soorma_si_abc.def.ghi';"),
    ).toEqual([]);
    expect(
      textFindings('f', "if (pem.startsWith('-----BEGIN PRIVATE KEY-----')) parse(pem);"),
    ).toEqual([]);
  });

  it('passes on the tracked files', () => {
    expect(repositoryFindings()).toEqual([]);
  });

  it('scans a tar stream, as docker export writes one', async () => {
    const dir = mkdtempSync(join(tmpdir(), 'soorma-tar-'));
    dirs.push(dir);
    mkdirSync(join(dir, 'app', 'deep'), { recursive: true });
    writeFileSync(join(dir, 'app', 'clean.txt'), 'nothing here');
    writeFileSync(join(dir, 'app', 'deep', 'leak.pem'), key);
    execFileSync('tar', ['-cf', join(dir, 'fs.tar'), '-C', dir, 'app']);
    const found = await tarFindings(createReadStream(join(dir, 'fs.tar')));
    expect(found.map((f) => f.location)).toEqual(['app/deep/leak.pem']);
  });
});

describe("TC-EHA-069: the code checks cover U4's packages, and === on a secret token fails them", () => {
  it('the real-tree checks above include service-kit, env-store, P4, P5, P7, and S2', () => {
    const projects = sourceProjects().map((p) => p.slice(repoRoot.length + 1));
    for (const project of [
      'packages/service-kit/tsconfig.json',
      'packages/env-store/tsconfig.json',
      'packages/registry/tsconfig.json',
      'packages/credentials/tsconfig.json',
      'packages/attribution/tsconfig.json',
      'services/control-gateway/tsconfig.json',
    ])
      expect(projects).toContain(project);
  });

  it('reports === on a SecretText token, even against undefined', () => {
    const root = tree({
      'token.ts': `declare const secretTextBrand: unique symbol;
export type SecretText = string & { readonly [secretTextBrand]: true };
export function f(token: SecretText | undefined, other: SecretText, n: number): boolean[] {
  return [token === undefined, token === other, n === 1];
}
`,
    });
    const lines = codeFindings('compare', root).map((f) => f.location);
    expect(lines).toHaveLength(2);
    expect(lines.every((l) => l.endsWith('token.ts:4'))).toBe(true);
  });
});

describe('TC-AR-028: no code path updates or deletes a registration or a secret', () => {
  it("no statement in U5's packages or S2 updates or deletes either table", () => {
    const sources = [
      'packages/registry/src',
      'packages/env-store/src',
      'services/control-gateway/src',
    ].flatMap((dir) =>
      readdirSync(join(repoRoot, dir), { recursive: true, encoding: 'utf8' })
        .filter((f) => f.endsWith('.ts'))
        .map((f) => join(repoRoot, dir, f)),
    );
    expect(sources.length).toBeGreaterThan(0);
    const writes = /\b(UPDATE|DELETE\s+FROM|TRUNCATE)\s+(registrations|registration_secrets)\b/i;
    const found = sources.filter((f) => writes.test(readFileSync(f, 'utf8')));
    expect(found).toEqual([]);
  });
});

describe("TC-AR-047, 071: U5's code holds no tenant identifier or topology read, and draws randomness only from randomBytes", () => {
  const files = [
    'services/control-gateway/src/edge/edge-handlers.ts',
    'packages/registry/src/registrations.ts',
    'packages/registry/src/registration-secret.ts',
    'packages/authority/src/registration.ts',
    'packages/authority/src/human.ts',
  ].map((f) => ({ file: f, text: readFileSync(join(repoRoot, f), 'utf8') }));
  const accepted = new Set([
    'agent:register',
    'credential:revoke',
    'agent:retire',
    'grant:human',
    'event:publish',
    'event:subscribe',
    'attribution:read',
    'human:manage',
    'agent:delegate',
  ]);

  it('every permission literal is plane-declared, never a tenant identifier (I9)', () => {
    for (const { file, text } of files)
      for (const [, literal] of text.matchAll(/'([a-z][a-z0-9._-]*(?::[a-z][a-z0-9._-]*)+)'/g))
        if (!literal!.startsWith('node:'))
          expect(accepted.has(literal!), `${file}: ${literal}`).toBe(true);
  });

  it('nothing reads a host, address, or deployment label (I3, I10)', () => {
    for (const { file, text } of files)
      expect(text, file).not.toMatch(/remoteAddress|hostname|x-forwarded|node:os|process\.env/i);
  });

  it('randomness only from crypto.randomBytes; digests compared only with timingSafeEqual', () => {
    for (const { file, text } of files)
      expect(text, file).not.toMatch(/Math\.random|getRandomValues|randomUUID/);
    const secret = files.find((f) => f.file.endsWith('registration-secret.ts'))!.text;
    expect(secret).toContain('randomBytes(32)');
    expect(secret).toContain('timingSafeEqual(');
  });
});

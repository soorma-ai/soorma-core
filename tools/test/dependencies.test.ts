// SPDX-License-Identifier: FSL-1.1-ALv2
// The dependency register and the licence check: TC-WC-038.
import { describe, expect, it } from 'vitest';
import {
  licenceFindings,
  parseLicenceExceptions,
  satisfies,
  type ResolvedPackage,
} from '../checks/licence.ts';
import { registerFindings } from '../checks/register.ts';
import { directDependencies, loadWorkspace, type DirectDependency } from '../checks/workspace.ts';

const workspace = loadWorkspace();
const direct = directDependencies(workspace.manifests);
const exceptions = parseLicenceExceptions(workspace.register);

const pkg = (
  name: string,
  licence: string,
  over: Partial<ResolvedPackage> = {},
): ResolvedPackage => ({
  name,
  version: '1.0.0',
  licence,
  runtime: false,
  direct: false,
  ...over,
});

describe('TC-WC-038: every dependency is registered', () => {
  it('step 1: every direct dependency has a row', () => {
    expect(direct.length).toBeGreaterThan(0);
    expect(registerFindings(direct, workspace.register)).toEqual([]);
  });

  it('step 2: the register records the openapi-typescript>typescript peer exception', () => {
    expect(workspace.register).toMatch(/\| `openapi-typescript>typescript`: `6` \|/);
  });

  it('requires a row for every override (D-CG-16)', () => {
    const overrides = workspace.settings.overrides as Record<string, string>;
    expect(Object.keys(overrides)).toEqual(['minimatch@>=7 <11.0.1']);
    expect(registerFindings(direct, workspace.register, overrides)).toEqual([]);
    expect(
      registerFindings(direct, workspace.register, { ...overrides, 'glob@<9': '9.0.0' }),
    ).toEqual([
      {
        check: 'register',
        location: 'pnpm-workspace.yaml: overrides: glob@<9',
        message: 'override with no row under "Overrides" in DEPENDENCIES.md',
      },
    ]);
  });

  it('step 3: refuses a direct dependency without a row, naming it', () => {
    const added: DirectDependency = {
      name: 'left-pad',
      version: '1.3.0',
      manifest: 'package.json',
      kind: 'development',
    };
    expect(registerFindings([...direct, added], workspace.register)).toEqual([
      {
        check: 'register',
        location: 'package.json: left-pad',
        message: 'direct dependency with no row in DEPENDENCIES.md',
      },
    ]);
  });
});

describe('TC-WC-038: licences by scope, and exceptions only through a row', () => {
  it('accepts the strict allowlist everywhere, and the wider list only for development-only transitive packages', () => {
    expect(
      licenceFindings([pkg('a', 'MIT', { direct: true }), pkg('b', 'ISC', { runtime: true })], []),
    ).toEqual([]);
    expect(licenceFindings([pkg('c', 'BlueOak-1.0.0'), pkg('d', 'Python-2.0')], [])).toEqual([]);
    expect(licenceFindings([pkg('e', 'BlueOak-1.0.0', { direct: true })], [])).toHaveLength(1);
    expect(licenceFindings([pkg('f', 'CC0-1.0', { runtime: true })], [])).toHaveLength(1);
  });

  it('reads SPDX expressions', () => {
    expect(satisfies('(MIT OR CC0-1.0)', ['MIT'])).toBe(true);
    expect(satisfies('MIT AND GPL-3.0-only', ['MIT'])).toBe(false);
  });

  it('step 4: refuses a dependency under a licence outside the allowlist, with no exception, naming it', () => {
    const findings = licenceFindings(
      [pkg('copyleft-lib', 'GPL-3.0-only', { direct: true })],
      exceptions,
    );
    expect(findings).toHaveLength(1);
    expect(findings[0]?.location).toBe('copyleft-lib@1.0.0');
  });

  it('step 5: accepts it once an exception row names it under that licence', () => {
    const row = '| `copyleft-lib` | GPL-3.0-only | Development only | test |\n';
    const withRow = parseLicenceExceptions(
      workspace.register.replace(
        '| `lightningcss`, `lightningcss-*` |',
        `${row}| \`lightningcss\`, \`lightningcss-*\` |`,
      ),
    );
    expect(withRow).toHaveLength(2);
    expect(
      licenceFindings([pkg('copyleft-lib', 'GPL-3.0-only', { direct: true })], withRow),
    ).toEqual([]);
  });
});

describe('Q-CG-2: the lightningcss exception is scoped by name and licence, not version', () => {
  it('names lightningcss and every lightningcss-* platform package under MPL-2.0', () => {
    expect(exceptions).toContainEqual({
      names: ['lightningcss', 'lightningcss-*'],
      licence: 'MPL-2.0',
    });
  });

  it('accepts a platform package not installed on this machine, at any version, through the row', () => {
    const linux = pkg('lightningcss-linux-x64-gnu', 'MPL-2.0', { version: '9.9.9' });
    expect(
      licenceFindings([linux, pkg('lightningcss', 'MPL-2.0', { version: '2.0.0' })], exceptions),
    ).toEqual([]);
  });

  it('refuses the same package under a different licence', () => {
    const findings = licenceFindings(
      [pkg('lightningcss-linux-x64-gnu', 'GPL-3.0-only')],
      exceptions,
    );
    expect(findings).toHaveLength(1);
    expect(findings[0]?.message).toContain('does not match its exception row (MPL-2.0)');
  });

  it('refuses an MPL-2.0 package the row does not name', () => {
    expect(licenceFindings([pkg('other-css-tool', 'MPL-2.0')], exceptions)).toHaveLength(1);
  });
});

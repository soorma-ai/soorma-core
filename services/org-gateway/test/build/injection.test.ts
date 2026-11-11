// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The build configuration's proof (D-CG-OI-02, amendment 1): a token and an
// injectable class in one package (@soorma/org-identity), and the module that
// provides them in this service. It must resolve under Vitest's default
// transform (from the packages' source), and under Node from the compiled
// dist/ (from the packages' compiled JavaScript), after `tsc -b` has built the
// packages in order from their declarations. The typecheck is the fourth
// leg, run by `pnpm run build`.
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Module } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { CLOCK, type Clock } from '@soorma/service-kit';
import { Lifetimes, SIGN_IN_LIFETIME_MS } from '@soorma/org-identity';
import { describe, expect, it } from 'vitest';
import { ClockModule } from '../../src/clock.module.ts';

const serviceRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const repoRoot = resolve(serviceRoot, '..', '..');

const fixed: Clock = { now: () => new Date('2026-11-08T12:00:00Z') };

@Module({ providers: [{ provide: CLOCK, useValue: fixed }, Lifetimes] })
class FixedClockModule {}

describe('D-CG-OI-02: injection across a package boundary', () => {
  it('under Vitest, resolves the class from the source with its clock injected', async () => {
    const app = await NestFactory.createApplicationContext(FixedClockModule, { logger: false });
    try {
      const lifetimes = app.get(Lifetimes);
      expect(lifetimes.signInExpiry(fixed.now()).toISOString()).toBe('2026-11-08T12:15:00.000Z');
      expect(lifetimes.signInExpiry(new Date('2026-11-08T00:05:00Z')).toISOString()).toBe(
        '2026-11-08T12:05:00.000Z',
      );
    } finally {
      await app.close();
    }
  });

  it("under Vitest, boots the service's own module", async () => {
    const app = await NestFactory.createApplicationContext(ClockModule, { logger: false });
    try {
      const before = Date.now();
      const expiry = app.get(Lifetimes).signInExpiry(new Date()).getTime();
      expect(expiry - before).toBeGreaterThanOrEqual(SIGN_IN_LIFETIME_MS);
      expect(expiry - before).toBeLessThan(SIGN_IN_LIFETIME_MS + 5_000);
    } finally {
      await app.close();
    }
  });

  it('builds with tsc -b in order, then resolves the class under Node from dist/', () => {
    const tsc = join(repoRoot, 'node_modules', 'typescript', 'bin', 'tsc');
    execFileSync(process.execPath, [tsc, '-b', join(serviceRoot, 'tsconfig.build.json')], {
      cwd: repoRoot,
      stdio: 'pipe',
    });
    expect(existsSync(join(repoRoot, 'packages/org-identity/dist/index.js'))).toBe(true);
    expect(existsSync(join(repoRoot, 'packages/org-identity/dist/index.d.ts'))).toBe(true);
    expect(existsSync(join(serviceRoot, 'dist/clock.module.js'))).toBe(true);

    // No loader and no flag: Node's own conditions, so @soorma/org-identity
    // resolves to packages/org-identity/dist/index.js.
    const script = `
      import { NestFactory } from '@nestjs/core';
      import { Lifetimes } from '@soorma/org-identity';
      import { ClockModule } from './dist/clock.module.js';
      const resolved = import.meta.resolve('@soorma/org-identity');
      const app = await NestFactory.createApplicationContext(ClockModule, { logger: false });
      const now = Date.now();
      const ms = app.get(Lifetimes).signInExpiry(new Date(now)).getTime() - now;
      await app.close();
      console.log(JSON.stringify({ resolved, ms }));
    `;
    const out = execFileSync(process.execPath, ['--input-type=module', '--eval', script], {
      cwd: serviceRoot,
      encoding: 'utf8',
      env: { PATH: process.env.PATH ?? '' },
    });
    const result = JSON.parse(out.trim().split('\n').pop()!) as { resolved: string; ms: number };
    expect(result.resolved).toMatch(/\/packages\/org-identity\/dist\/index\.js$/);
    expect(result.ms).toBeGreaterThanOrEqual(SIGN_IN_LIFETIME_MS);
    expect(result.ms).toBeLessThan(SIGN_IN_LIFETIME_MS + 5_000);
  }, 120_000);
});

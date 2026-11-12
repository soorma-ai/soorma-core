// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The throwaway test database (Q-CG-2 A; D-CG-OI-15):
//
//   pnpm db:test         start postgres (pinned by digest) on a random
//                        loopback port, with tmpfs storage, and print
//                        TEST_DATABASE_URL (its superuser), and
//                        TEST_DATABASE_CONTAINER (its container, U5)
//   pnpm db:test:stop    remove it
//
// No TLS: TLS to the database is verified only by the stack smoke test. The
// superuser password is random per start, passed to the container as a
// mounted file (never an environment variable), and deleted once the server
// is ready. The test harness creates the roles and migrates (D-CG-OI-15).
import { execFileSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

/** postgres 18.4, pinned by its image index digest (D-CG-OI-10; pushed 2026-08-06). */
export const POSTGRES_IMAGE =
  'postgres:18.4@sha256:a02db8cac496f15b094798a38254f14d6e00741f709360e5e00bb6668ea31636';
export const CONTAINER = 'soorma-db-test';

function docker(args: string[]): string {
  return execFileSync('docker', args, {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trim();
}

function running(): boolean {
  return docker(['ps', '-q', '--filter', `name=^${CONTAINER}$`]).length > 0;
}

function stop(): void {
  if (docker(['ps', '-aq', '--filter', `name=^${CONTAINER}$`]).length > 0) {
    docker(['rm', '-f', CONTAINER]);
    console.log(`Removed ${CONTAINER}.`);
  } else {
    console.log(`${CONTAINER} is not running.`);
  }
}

async function start(): Promise<void> {
  if (running()) {
    console.error(`${CONTAINER} is already running. Run pnpm db:test:stop first.`);
    process.exitCode = 1;
    return;
  }
  const password = randomBytes(24).toString('base64url');
  const dir = mkdtempSync(join(tmpdir(), 'soorma-db-test-'));
  const passwordFile = join(dir, 'password');
  writeFileSync(passwordFile, password, { mode: 0o600 });
  try {
    docker([
      'run',
      '--detach',
      '--rm',
      '--name',
      CONTAINER,
      '--publish',
      '127.0.0.1::5432',
      '--tmpfs',
      '/var/lib/postgresql:rw',
      '--volume',
      `${passwordFile}:/run/secrets/postgres-password:ro`,
      '--env',
      'POSTGRES_PASSWORD_FILE=/run/secrets/postgres-password',
      POSTGRES_IMAGE,
    ]);
    for (let i = 0; i < 120; i++) {
      try {
        docker(['exec', CONTAINER, 'pg_isready', '-q', '-h', '127.0.0.1', '-U', 'postgres']);
        const port = docker(['port', CONTAINER, '5432/tcp']).split('\n')[0]!.split(':').pop()!;
        console.log(`TEST_DATABASE_URL=postgres://postgres:${password}@127.0.0.1:${port}/postgres`);
        // The server's container, for tests that run its pg_dump and pg_restore (U5 D-CG-AR-04).
        console.log(`TEST_DATABASE_CONTAINER=${CONTAINER}`);
        return;
      } catch {
        await new Promise((r) => setTimeout(r, 500));
      }
    }
    throw new Error(`${CONTAINER} did not become ready`);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

if (import.meta.main) {
  const command = process.argv[2];
  if (command === 'start') {
    start().catch((error: unknown) => {
      console.error(error instanceof Error ? error.message : error);
      process.exitCode = 1;
    });
  } else if (command === 'stop') {
    stop();
  } else {
    console.error('usage: node deploy/local/scripts/db-test.ts <start|stop>');
    process.exitCode = 2;
  }
}

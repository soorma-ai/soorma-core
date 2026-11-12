// SPDX-License-Identifier: FSL-1.1-ALv2
//
// pnpm stack:backup <env> (U5 NFR-AR-09; NP-AR-08): a custom-format dump of an
// environment's store, as its migrator role, through the one-shot {env}-backup
// service, which mounts only its backup/ secrets subpath and reads the
// password through a pgpass file.
//
// - `docker compose run --rm -T`: no terminal, so the binary stream is not
//   altered; the service's stdout is the dump, its stderr the console's
// - The file is created here, 0600 from the moment it is opened, in the
//   git-ignored deploy/local/.backups/ (0700). It contains human identifiers
// - Then the archive validity check (PGDMP; a full read, pg_restore
//   --file=/dev/null, exits 0; D-CG-AR-20).
//   A failed dump or check deletes the file and fails
import { spawn } from 'node:child_process';
import { createReadStream, createWriteStream, unlinkSync } from 'node:fs';
import {
  BACKUP_DIR,
  checkArchive,
  ENVIRONMENT_ID,
  FULL_READ,
  openBackupFile,
} from './backup-archive.ts';
import { COMPOSE } from './stack-client.ts';

const PROFILE = ['--profile', 'backup'];

/** `stdin`: a file to stream in, or null for none. `stdout`: a file descriptor, or null to discard. */
function run(args: string[], stdin: string | null, stdout: number | null): Promise<number> {
  return new Promise((resolve, reject) => {
    const child = spawn('docker', [...COMPOSE, ...PROFILE, ...args], {
      stdio: [stdin === null ? 'ignore' : 'pipe', stdout === null ? 'ignore' : 'pipe', 'inherit'],
    });
    if (stdin !== null) createReadStream(stdin).pipe(child.stdin!);
    if (stdout !== null) child.stdout!.pipe(createWriteStream('', { fd: stdout }));
    child.on('error', reject);
    child.on('close', (code) => resolve(code ?? 1));
  });
}

/** The full read in the backup service's image, the file on stdin; no connection. */
export function readArchive(env: string): (path: string) => Promise<number> {
  return (path) =>
    run(
      [
        'run',
        '--rm',
        '-T',
        '--no-deps',
        '--entrypoint',
        FULL_READ[0],
        `${env}-backup`,
        ...FULL_READ.slice(1),
      ],
      path,
      null,
    );
}

export async function backup(env: string, dir = BACKUP_DIR): Promise<string> {
  if (!ENVIRONMENT_ID.test(env)) throw new Error(`not an environment id: ${env}`);
  const name = `${env}-${new Date().toISOString().replace(/[:.]/g, '-')}.dump`;
  const { path, fd } = openBackupFile(dir, name);
  const code = await run(['run', '--rm', '-T', '--no-deps', `${env}-backup`], null, fd);
  if (code !== 0) {
    unlinkSync(path);
    throw new Error(`the backup of ${env} failed (exit ${code}); nothing was kept`);
  }
  const check = await checkArchive(path, readArchive(env));
  if (!check.ok) {
    unlinkSync(path);
    throw new Error(`the backup of ${env} is not a valid archive (${check.reason}); deleted`);
  }
  return path;
}

if (import.meta.main) {
  const env = process.argv[2] ?? '';
  backup(env)
    .then((path) => {
      console.log(`Backed up ${env} to ${path} (mode 0600). It contains human identifiers.`);
    })
    .catch((error: unknown) => {
      console.error(error instanceof Error ? error.message : String(error));
      process.exit(1);
    });
}

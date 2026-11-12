// SPDX-License-Identifier: FSL-1.1-ALv2
//
// pnpm stack:restore <env> <file> (U5 NFR-AR-09; NP-AR-08): restores a dump
// into an environment's EMPTY store, through the one-shot {env}-restore
// service, the file streamed to its stdin. The service refuses a database that
// is not empty, then restores in one transaction, stopping at the first error.
import { spawn } from 'node:child_process';
import { createReadStream } from 'node:fs';
import { ENVIRONMENT_ID } from './backup-archive.ts';
import { COMPOSE } from './stack-client.ts';

export function restore(env: string, path: string): Promise<number> {
  if (!ENVIRONMENT_ID.test(env)) throw new Error(`not an environment id: ${env}`);
  return new Promise((resolve, reject) => {
    const child = spawn(
      'docker',
      [...COMPOSE, '--profile', 'backup', 'run', '--rm', '-T', '--no-deps', `${env}-restore`],
      { stdio: ['pipe', 'inherit', 'inherit'] },
    );
    createReadStream(path).pipe(child.stdin);
    child.on('error', reject);
    child.on('close', (code) => resolve(code ?? 1));
  });
}

if (import.meta.main) {
  const [env = '', path = ''] = process.argv.slice(2);
  restore(env, path)
    .then((code) => {
      if (code !== 0) {
        console.error(`the restore of ${env} failed (exit ${code})`);
        process.exit(code);
      }
      console.log(`Restored ${env} from ${path}.`);
    })
    .catch((error: unknown) => {
      console.error(error instanceof Error ? error.message : String(error));
      process.exit(1);
    });
}

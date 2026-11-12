// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Backup files and the archive validity check (U5 NFR-AR-09; NP-AR-08, 09):
//
// - A dump contains human identifiers (sponsors, issuers, attribution
//   actors), so it is written only under deploy/local/.backups/ (git-ignored
//   and docker-ignored), the directory 0700 and the file 0600 from the moment
//   it is opened (flags wx), and never into the repository
// - After every backup, the archive validity check: the file must begin with
//   the custom-format magic bytes PGDMP, and a full read, `pg_restore
//   --file=/dev/null` (every block, restored to nowhere, no connection), must
//   exit 0 (D-CG-AR-20). It catches a dump damaged in transit: a terminal, or
//   diagnostics in the stream, or a lost tail. `pg_restore --list` alone
//   would not: it reads only the header and table of contents. The round
//   trip proves the data survives
import { chmodSync, closeSync, mkdirSync, openSync, readSync } from 'node:fs';
import { join, resolve } from 'node:path';

export const BACKUP_DIR = join(resolve(import.meta.dirname, '..'), '.backups');

/** The custom-format archive's first five bytes. */
export const ARCHIVE_MAGIC = Buffer.from('PGDMP', 'ascii');

/** An environment id, as env.sh accepts one. */
export const ENVIRONMENT_ID = /^[a-z0-9-]+$/;

/** Creates (or resets) the directory 0700, and opens a new file in it 0600, failing if it exists. */
export function openBackupFile(dir: string, name: string): { path: string; fd: number } {
  mkdirSync(dir, { recursive: true, mode: 0o700 });
  chmodSync(dir, 0o700);
  const path = join(dir, name);
  return { path, fd: openSync(path, 'wx', 0o600) };
}

/** Whether the file begins with the custom-format magic. */
export function hasArchiveMagic(path: string): boolean {
  const fd = openSync(path, 'r');
  try {
    const head = Buffer.alloc(ARCHIVE_MAGIC.length);
    const read = readSync(fd, head, 0, head.length, 0);
    return read === head.length && head.equals(ARCHIVE_MAGIC);
  } finally {
    closeSync(fd);
  }
}

export type ArchiveCheck = { ok: true } | { ok: false; reason: 'magic' | 'read' };

/** The full read's arguments: every block of the archive on stdin, restored to nowhere. */
export const FULL_READ = ['pg_restore', '--file=/dev/null'] as const;

/**
 * The archive validity check: the magic, then the full read, run by `read`
 * with the file on its stdin and resolving to its exit code (D-CG-AR-20).
 */
export async function checkArchive(
  path: string,
  read: (path: string) => Promise<number>,
): Promise<ArchiveCheck> {
  if (!hasArchiveMagic(path)) return { ok: false, reason: 'magic' };
  if ((await read(path)) !== 0) return { ok: false, reason: 'read' };
  return { ok: true };
}

// SPDX-License-Identifier: FSL-1.1-ALv2
// #26: the linear tar reader against the reader it replaced, on real exported
// images: the same files, in the same order, with the same sizes and content.
// Run locally, not in CI (it needs the built images, and the old reader takes
// minutes an image):
//
//   SOORMA_TAR_COMPARE=soorma/org-gateway:local,soorma/control-gateway:local,soorma/data-gateway:local,soorma/event-ingest:local \
//     pnpm vitest run tools/test/tar-compare.test.ts --silent=false
//
// The old reader is read from git at 0095523 (the commit before #26), so the
// repository keeps no copy of it.
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createReadStream, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { afterAll, describe, expect, it } from 'vitest';
import { walkTar, type TarFile } from '../checks/tar.ts';
import { repoRoot } from '../checks/workspace.ts';

const OLD_READER_COMMIT = '0095523';
const images = (process.env.SOORMA_TAR_COMPARE ?? '').split(',').filter((i) => i.length > 0);

type Walk = (stream: AsyncIterable<Buffer>, onFile: (file: TarFile) => void) => Promise<void>;

describe.skipIf(images.length === 0)(
  '#26: the linear reader reads real images as the old one did',
  () => {
    const dir = mkdtempSync(join(tmpdir(), 'soorma-tar-compare-'));
    afterAll(() => rmSync(dir, { recursive: true, force: true }));

    async function listing(
      walk: Walk,
      file: string,
    ): Promise<{ lines: string[]; seconds: number }> {
      const lines: string[] = [];
      const start = performance.now();
      await walk(createReadStream(file), (f) =>
        lines.push(
          `${f.name}\t${f.size}\t${f.content ? createHash('sha256').update(f.content).digest('hex') : '-'}`,
        ),
      );
      return { lines, seconds: (performance.now() - start) / 1000 };
    }

    for (const image of images) {
      it(
        image,
        async () => {
          const oldPath = join(dir, 'tar-old.ts');
          writeFileSync(
            oldPath,
            execFileSync('git', ['show', `${OLD_READER_COMMIT}:tools/checks/tar.ts`], {
              cwd: repoRoot,
            }),
          );
          const old = (await import(pathToFileURL(oldPath).href)) as { walkTar: Walk };

          const archive = join(dir, 'fs.tar');
          const id = execFileSync('docker', ['create', image], { encoding: 'utf8' }).trim();
          try {
            execFileSync('docker', ['export', '-o', archive, id]);
          } finally {
            execFileSync('docker', ['rm', id], { stdio: 'ignore' });
          }

          const now = await listing(walkTar, archive);
          const before = await listing(old.walkTar, archive);
          console.log(
            `${image}: ${now.lines.length} files; linear ${now.seconds.toFixed(2)} s, ` +
              `old ${before.seconds.toFixed(2)} s; identical ${JSON.stringify(now.lines) === JSON.stringify(before.lines)}`,
          );
          expect(now.lines.length).toBeGreaterThan(0);
          expect(now.lines).toEqual(before.lines);
        },
        600_000,
      );
    }
  },
);

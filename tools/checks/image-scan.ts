// SPDX-License-Identifier: FSL-1.1-ALv2
//
// One export, one pass (#26): a built image's file system is exported once and
// read once, and that one pass gives both the secret-pattern findings
// (D-ID-OI-07, 09; secrets.ts) and the installed-packages findings (U6
// NP-AC-10; D-CG-AC-11; image-packages.ts), each with its own logic unchanged.
//
//   node tools/checks/run.ts secrets image-packages --image <ref> --forbid <names>
//
// docker export's exit status is checked: an export that fails or is cut short
// is an error, never a scan of the files that happened to arrive.
import { execFileSync, spawn } from 'node:child_process';
import { once } from 'node:events';
import { packageFindings, type PackageQuery } from './image-packages.ts';
import { textFindings } from './secrets.ts';
import { walkTar, type TarFile } from './tar.ts';
import type { Finding } from './workspace.ts';

export interface ImageScan {
  /** Run the secret patterns over every file's content. */
  readonly secrets: boolean;
  /** Run the installed-packages check with this query. */
  readonly packages?: PackageQuery;
}

export interface ImageScanFindings {
  readonly secrets: Finding[];
  readonly packages: Finding[];
}

const PACKAGE_JSON = /(^|\/)package\.json$/;

/** One walk of one tar stream (an exported file system), for both checks. */
export async function scanTar(
  stream: AsyncIterable<Buffer>,
  image: string,
  scan: ImageScan,
): Promise<ImageScanFindings> {
  const secrets: Finding[] = [];
  const files: TarFile[] = [];
  await walkTar(stream, (file) => {
    if (scan.secrets && file.content) {
      for (const f of textFindings(file.name, file.content.toString('latin1')))
        secrets.push({ ...f, location: `${image}:/${f.location}` });
    }
    if (scan.packages) {
      files.push({
        name: file.name,
        size: file.size,
        // Only package.json content is read; every other file is a name.
        content: PACKAGE_JSON.test(file.name) ? file.content : undefined,
      });
    }
  });
  return {
    secrets,
    packages: scan.packages ? packageFindings(image, files, scan.packages) : [],
  };
}

/** Exports `image` once (docker create, docker export, docker rm) and scans it in one pass. */
export async function imageScanFindings(
  image: string,
  scan: ImageScan,
): Promise<ImageScanFindings> {
  if (scan.packages && scan.packages.forbid.length + scan.packages.expect.length === 0)
    throw new Error('the installed-packages check names no package');
  const id = execFileSync('docker', ['create', image], { encoding: 'utf8' }).trim();
  try {
    const exported = spawn('docker', ['export', id], { stdio: ['ignore', 'pipe', 'inherit'] });
    const exit = once(exported, 'close') as Promise<[number | null, NodeJS.Signals | null]>;
    // Awaited below; marked handled now so a spawn error is not reported as
    // unhandled while the stream is still being read.
    exit.catch(() => undefined);
    const findings = await scanTar(exported.stdout as AsyncIterable<Buffer>, image, scan);
    const [code, signal] = await exit;
    if (code !== 0)
      throw new Error(
        `docker export of ${image} failed (${signal ?? `exit ${code}`}): not scanned`,
      );
    return findings;
  } finally {
    execFileSync('docker', ['rm', id], { stdio: 'ignore' });
  }
}

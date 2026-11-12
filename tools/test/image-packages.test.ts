// SPDX-License-Identifier: FSL-1.1-ALv2
// The installed-packages check (U6 NP-AC-10; D-CG-AC-11; TC-AC-083, the
// check's own half) and the shared tar reader. The images themselves are
// checked in CI's image job.
import { Readable } from 'node:stream';
import { describe, expect, it } from 'vitest';
import { heldPackages, packageFindings } from '../checks/image-packages.ts';
import { walkTar, type TarFile } from '../checks/tar.ts';

/** A minimal tar archive: each entry a 512-byte header, then its padded content. */
function tar(entries: { name: string; content?: string; type?: string }[]): Buffer {
  const blocks: Buffer[] = [];
  const header = (name: string, size: number, type: string): Buffer => {
    const h = Buffer.alloc(512);
    h.write(name.slice(0, 100), 0, 'utf8');
    h.write(size.toString(8).padStart(11, '0') + '\0', 124, 'utf8');
    h.write(type, 156, 'utf8');
    return h;
  };
  const body = (text: string): Buffer => {
    const b = Buffer.from(text, 'utf8');
    return Buffer.concat([b, Buffer.alloc(Math.ceil(b.length / 512) * 512 - b.length)]);
  };
  for (const e of entries) {
    const content = e.content ?? '';
    if (e.name.length > 100) {
      blocks.push(header('././@LongLink', e.name.length, 'L'), body(e.name));
    }
    blocks.push(header(e.name, Buffer.byteLength(content), e.type ?? '0'), body(content));
  }
  blocks.push(Buffer.alloc(1024));
  return Buffer.concat(blocks);
}

async function files(archive: Buffer): Promise<TarFile[]> {
  const out: TarFile[] = [];
  await walkTar(Readable.from([archive]), (f) => out.push(f));
  return out;
}

const pkg = (name: string): string => JSON.stringify({ name, version: '0.0.0' });

describe('the tar reader', () => {
  it('reads regular files with their content, a long name, and skips directories', async () => {
    const long = `app/node_modules/${'x'.repeat(120)}/package.json`;
    const read = await files(
      tar([
        { name: 'app/', type: '5' },
        { name: 'app/main.js', content: 'run()' },
        { name: long, content: pkg('x') },
      ]),
    );
    expect(read.map((f) => f.name)).toEqual(['app/main.js', long]);
    expect(read[0]!.content?.toString()).toBe('run()');
  });
});

describe('TC-AC-083: which workspace packages an image holds', () => {
  const S1 = 'soorma/org-gateway:local';

  it('finds a package by its directory, in either layout, or by a package.json name', async () => {
    const read = await files(
      tar([
        { name: 'app/node_modules/@soorma/org-identity/dist/index.js', content: '' },
        { name: 'app/node_modules/.pnpm/@soorma+identity-resolution@0.0.0/x.js', content: '' },
        { name: 'app/vendor/renamed/package.json', content: pkg('@soorma/abuse-bound') },
        {
          name: 'app/node_modules/@soorma/service-kit/package.json',
          content: pkg('@soorma/service-kit'),
        },
      ]),
    );
    expect(
      [
        ...heldPackages(read, [
          '@soorma/org-identity',
          '@soorma/identity-resolution',
          '@soorma/abuse-bound',
          '@soorma/authority',
        ]),
      ].sort(),
    ).toEqual(['@soorma/abuse-bound', '@soorma/identity-resolution', '@soorma/org-identity']);
  });

  it('a forbidden package held is a finding; one absent is not', async () => {
    const read = await files(
      tar([
        {
          name: 'app/node_modules/@soorma/org-identity/package.json',
          content: pkg('@soorma/org-identity'),
        },
      ]),
    );
    expect(packageFindings('s2', read, { forbid: ['@soorma/org-identity'], expect: [] })).toEqual([
      { check: 'image-packages', location: 's2', message: 'holds @soorma/org-identity' },
    ]);
    expect(
      packageFindings('s3', read, { forbid: ['@soorma/identity-resolution'], expect: [] }),
    ).toEqual([]);
  });

  it('an expected package absent is a finding, so the positive control is never vacuous', async () => {
    const read = await files(tar([{ name: 'app/main.js', content: '' }]));
    expect(packageFindings(S1, read, { forbid: [], expect: ['@soorma/org-identity'] })).toEqual([
      { check: 'image-packages', location: S1, message: 'does not hold @soorma/org-identity' },
    ]);
  });

  it('a package whose name only begins the same is not held', async () => {
    const read = await files(
      tar([{ name: 'app/node_modules/@soorma/org-identity-extra/index.js', content: '' }]),
    );
    expect(heldPackages(read, ['@soorma/org-identity']).size).toBe(0);
  });
});

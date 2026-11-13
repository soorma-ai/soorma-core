// SPDX-License-Identifier: FSL-1.1-ALv2
// #26: one export and one pass per image (image-scan.ts), and the linear tar
// reader. The images themselves are checked in CI's image job; these tests add
// to, and change nothing in, the checks' existing tests.
import { generateKeyPairSync } from 'node:crypto';
import { Readable } from 'node:stream';
import { describe, expect, it } from 'vitest';
import { scanTar } from '../checks/image-scan.ts';
import { TAR_CONTENT_LIMIT, walkTar, type TarFile } from '../checks/tar.ts';

/** A 512-byte ustar-style header: a name, a size, a type. */
function header(name: string, size: number, type = '0'): Buffer {
  const h = Buffer.alloc(512);
  h.write(name.slice(0, 100), 0, 'utf8');
  h.write(size.toString(8).padStart(11, '0') + '\0', 124, 'utf8');
  h.write(type, 156, 'utf8');
  return h;
}

/** Content padded to the next 512-byte block. */
function body(content: string | Buffer): Buffer {
  const b = typeof content === 'string' ? Buffer.from(content, 'utf8') : content;
  return Buffer.concat([b, Buffer.alloc(Math.ceil(b.length / 512) * 512 - b.length)]);
}

function tar(entries: { name: string; content: string }[]): Buffer {
  return Buffer.concat([
    ...entries.flatMap((e) => [header(e.name, Buffer.byteLength(e.content)), body(e.content)]),
    Buffer.alloc(1024),
  ]);
}

/** A stream that can be read only once: a second read throws. */
function once(archive: Buffer): AsyncIterable<Buffer> & { reads: number } {
  const stream = {
    reads: 0,
    [Symbol.asyncIterator](): AsyncIterator<Buffer> {
      stream.reads += 1;
      if (stream.reads > 1) throw new Error('the stream was read twice');
      let sent = false;
      return {
        next: () =>
          Promise.resolve(
            sent
              ? { done: true, value: undefined }
              : ((sent = true), { done: false, value: archive }),
          ),
      };
    },
  };
  return stream;
}

const pkg = (name: string): string => JSON.stringify({ name, version: '0.0.0' });

describe('#26: one pass over one export gives both sets of findings', () => {
  // Generated at run time, as code-checks.test.ts does: no key in the source.
  const key = generateKeyPairSync('ed25519')
    .privateKey.export({ format: 'pem', type: 'pkcs8' })
    .toString();

  it('finds a planted secret and a forbidden package, and a missing expected one, reading the stream once', async () => {
    const stream = once(
      tar([
        { name: 'app/main.js', content: 'run()' },
        { name: 'app/leak.pem', content: key },
        {
          name: 'app/node_modules/@soorma/org-identity/package.json',
          content: pkg('@soorma/org-identity'),
        },
      ]),
    );
    const found = await scanTar(stream, 'img', {
      secrets: true,
      packages: { forbid: ['@soorma/org-identity'], expect: ['@soorma/abuse-bound'] },
    });
    expect(stream.reads).toBe(1);
    expect(found).toEqual({
      secrets: [
        { check: 'secrets', location: 'img:/app/leak.pem', message: 'holds a private key' },
      ],
      packages: [
        { check: 'image-packages', location: 'img', message: 'holds @soorma/org-identity' },
        { check: 'image-packages', location: 'img', message: 'does not hold @soorma/abuse-bound' },
      ],
    });
  });

  it('a clean image gives no finding from either check', async () => {
    const found = await scanTar(
      once(
        tar([
          { name: 'app/main.js', content: 'run()' },
          {
            name: 'app/node_modules/@soorma/service-kit/package.json',
            content: pkg('@soorma/service-kit'),
          },
        ]),
      ),
      'img',
      { secrets: true, packages: { forbid: ['@soorma/org-identity'], expect: [] } },
    );
    expect(found).toEqual({ secrets: [], packages: [] });
  });
});

describe('#26: the tar reader streams an entry far over the limit in bounded memory', () => {
  const BIG = 64 * 2 ** 20; // four times TAR_CONTENT_LIMIT
  const CHUNK = 4093; // odd, so headers and content straddle chunk boundaries
  const AFTER = 'console.log("after the big file")';
  const MANIFEST = pkg('@soorma/x');

  /**
   * The archive as segments: bytes, or a run of zeros. Streamed lazily in
   * CHUNK-byte chunks; a chunk wholly inside a run of zeros is a view of one
   * shared zero buffer, so the stream itself allocates almost nothing and
   * arrayBuffers growth is what the reader holds.
   */
  function* chunks(segments: (Buffer | number)[], sample: () => void): Generator<Buffer> {
    const zero = Buffer.alloc(CHUNK);
    const total = segments.reduce<number>((n, s) => n + (typeof s === 'number' ? s : s.length), 0);
    const starts: number[] = [];
    segments.reduce<number>(
      (n, s) => (starts.push(n), n + (typeof s === 'number' ? s : s.length)),
      0,
    );
    let count = 0;
    for (let at = 0; at < total; at += CHUNK) {
      const end = Math.min(at + CHUNK, total);
      const i = starts.findLastIndex((s) => s <= at);
      const seg = segments[i]!;
      const segEnd = starts[i]! + (typeof seg === 'number' ? seg : seg.length);
      if (typeof seg === 'number' && end <= segEnd) {
        yield zero.subarray(0, end - at);
      } else {
        const out = Buffer.alloc(end - at);
        for (let j = i; j < segments.length && starts[j]! < end; j++) {
          const s = segments[j]!;
          if (typeof s === 'number') continue; // already zero
          const from = Math.max(at, starts[j]!);
          const to = Math.min(end, starts[j]! + s.length);
          s.copy(out, from - at, from - starts[j]!, to - starts[j]!);
        }
        yield out;
      }
      if (++count % 256 === 0) sample();
    }
  }

  it('lists it with no content, reads the files after it, and holds under 4 MiB', async () => {
    expect(BIG).toBeGreaterThan(TAR_CONTENT_LIMIT);
    const segments: (Buffer | number)[] = [
      header('app/big.bin', BIG),
      BIG,
      header('app/after.js', Buffer.byteLength(AFTER)),
      body(AFTER),
      header('app/node_modules/@soorma/x/package.json', Buffer.byteLength(MANIFEST)),
      body(MANIFEST),
      1024,
    ];
    const baseline = process.memoryUsage().arrayBuffers;
    let peak = 0;
    const sample = (): void => {
      peak = Math.max(peak, process.memoryUsage().arrayBuffers - baseline);
    };
    const read: TarFile[] = [];
    // Readable.from pulls the chunks one at a time, as a stream delivers them.
    await walkTar(Readable.from(chunks(segments, sample), { objectMode: true }), (f) => {
      sample();
      read.push(f);
    });
    sample();

    expect(read.map((f) => [f.name, f.size, f.content?.toString('utf8')])).toEqual([
      ['app/big.bin', BIG, undefined],
      ['app/after.js', Buffer.byteLength(AFTER), AFTER],
      ['app/node_modules/@soorma/x/package.json', Buffer.byteLength(MANIFEST), MANIFEST],
    ]);
    // The growth seen, for the record (#26: 20 local runs before the first commit).
    console.log(`tar reader: peak arrayBuffers growth ${(peak / 2 ** 20).toFixed(3)} MiB`);
    expect(peak).toBeLessThan(4 * 2 ** 20);
  });
});

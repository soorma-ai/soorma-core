// SPDX-License-Identifier: FSL-1.1-ALv2
//
// A tar stream reader (an exported container file system), shared by the
// secrets check and the image-packages check (U6 D-CG-AC-11). Extracted from
// U2's secrets check; its behaviour is unchanged: regular files only, a GNU
// long name ('L') applies to the next entry, files over the size limit are
// listed with no content.
//
// Linear in the stream's size (#26): incoming chunks are queued, never
// re-concatenated; an entry whose content is returned is copied out once, when
// all its bytes have arrived; bytes never returned (a file over the limit, a
// directory, a link, any other entry type) are dropped as they arrive. The
// reader it replaces concatenated its whole buffer on every chunk, which was
// quadratic in an image's largest file (the Node binary, about 150 MB).
export interface TarFile {
  readonly name: string;
  readonly size: number;
  /** The content, or undefined when the file is over the size limit. */
  readonly content: Buffer | undefined;
}

export const TAR_CONTENT_LIMIT = 16 * 2 ** 20;

interface Entry {
  readonly name: string;
  readonly size: number;
  readonly regular: boolean;
  readonly long: boolean;
  /** Whether the content is returned (and so kept until it is complete). */
  readonly keep: boolean;
  /** The entry's padded bytes still to come. */
  left: number;
}

/** Calls `onFile` for each regular file in the stream, in order. */
export async function walkTar(
  stream: AsyncIterable<Buffer>,
  onFile: (file: TarFile) => void,
): Promise<void> {
  const queue: Buffer[] = [];
  let queued = 0;
  let pending: Entry | undefined;
  let longName: string | undefined;

  /** Removes n queued bytes (n <= queued) from the front; returns them only when kept. */
  const take = (n: number, keep: boolean): Buffer | undefined => {
    if (n === 0) return keep ? Buffer.alloc(0) : undefined;
    const whole = keep && queue[0]!.length >= n;
    const out = whole ? queue[0]!.subarray(0, n) : keep ? Buffer.allocUnsafe(n) : undefined;
    let done = 0;
    while (done < n) {
      const chunk = queue[0]!;
      const k = Math.min(chunk.length, n - done);
      if (out && !whole) chunk.copy(out, done, 0, k);
      done += k;
      if (k === chunk.length) queue.shift();
      else queue[0] = chunk.subarray(k);
    }
    queued -= n;
    return out;
  };

  for await (const chunk of stream) {
    if (chunk.length === 0) continue;
    queue.push(chunk);
    queued += chunk.length;
    for (;;) {
      if (!pending) {
        if (queued < 512) break;
        const header = take(512, true)!;
        if (header.every((b) => b === 0)) continue;
        const field = (start: number, length: number): string =>
          header
            .subarray(start, start + length)
            .toString('utf8')
            .replace(/\0.*$/s, '');
        const prefix = field(345, 155);
        const type = field(156, 1);
        const size = parseInt(field(124, 12).trim() || '0', 8);
        const left = Math.ceil(size / 512) * 512;
        if (type === 'L') {
          pending = { name: '', size, regular: false, long: true, keep: true, left };
        } else {
          const name = longName ?? (prefix ? `${prefix}/${field(0, 100)}` : field(0, 100));
          longName = undefined;
          const regular = type === '0' || type === '';
          const keep = regular && size <= TAR_CONTENT_LIMIT;
          pending = { name, size, regular, long: false, keep, left };
        }
      }
      if (pending.keep) {
        if (queued < pending.left) break;
        const content = take(pending.left, true)!.subarray(0, pending.size);
        if (pending.long) longName = content.toString('utf8').replace(/\0.*$/s, '');
        else onFile({ name: pending.name, size: pending.size, content });
      } else {
        const n = Math.min(queued, pending.left);
        take(n, false);
        pending.left -= n;
        if (pending.left > 0) break;
        if (pending.regular) onFile({ name: pending.name, size: pending.size, content: undefined });
      }
      pending = undefined;
    }
  }
}

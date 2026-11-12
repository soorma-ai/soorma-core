// SPDX-License-Identifier: FSL-1.1-ALv2
//
// A tar stream reader (an exported container file system), shared by the
// secrets check and the image-packages check (U6 D-CG-AC-11). Extracted from
// U2's secrets check; its behaviour is unchanged: regular files only, a GNU
// long name ('L') applies to the next entry, files over the size limit are
// listed with no content.
export interface TarFile {
  readonly name: string;
  readonly size: number;
  /** The content, or undefined when the file is over the size limit. */
  readonly content: Buffer | undefined;
}

export const TAR_CONTENT_LIMIT = 16 * 2 ** 20;

/** Calls `onFile` for each regular file in the stream, in order. */
export async function walkTar(
  stream: AsyncIterable<Buffer>,
  onFile: (file: TarFile) => void,
): Promise<void> {
  let buffer = Buffer.alloc(0);
  let pending: { name: string; size: number; regular: boolean; long: boolean } | undefined;
  let longName: string | undefined;
  const take = (n: number): Buffer => {
    const out = buffer.subarray(0, n);
    buffer = buffer.subarray(n);
    return out;
  };
  for await (const chunk of stream) {
    buffer = Buffer.concat([buffer, chunk]);
    for (;;) {
      if (!pending) {
        if (buffer.length < 512) break;
        const header = take(512);
        if (header.every((b) => b === 0)) continue;
        const field = (start: number, length: number): string =>
          header
            .subarray(start, start + length)
            .toString('utf8')
            .replace(/\0.*$/s, '');
        const prefix = field(345, 155);
        const type = field(156, 1);
        const size = parseInt(field(124, 12).trim() || '0', 8);
        if (type === 'L') {
          pending = { name: '', size, regular: false, long: true };
        } else {
          const name = longName ?? (prefix ? `${prefix}/${field(0, 100)}` : field(0, 100));
          longName = undefined;
          pending = { name, size, regular: type === '0' || type === '', long: false };
        }
      }
      const padded = Math.ceil(pending.size / 512) * 512;
      if (buffer.length < padded) break;
      const content = take(padded).subarray(0, pending.size);
      if (pending.long) longName = content.toString('utf8').replace(/\0.*$/s, '');
      else if (pending.regular)
        onFile({
          name: pending.name,
          size: pending.size,
          content: pending.size > TAR_CONTENT_LIMIT ? undefined : content,
        });
      pending = undefined;
    }
  }
}

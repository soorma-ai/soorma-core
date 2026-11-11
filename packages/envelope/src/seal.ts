// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The envelope seal and the key ring (U3 NFR Design NP-01, NP-02; NFR-AE-17,
// 18; BR-FX-02; BR-ST-07).
//
// Form: v1.{kid}.{mac}, at most 63 characters.
// - kid: ^[A-Za-z0-9][A-Za-z0-9_-]{0,15}$, operator-assigned, no "."
// - mac: HMAC-SHA-256(key, "soorma.envelope-seal.v1" || 0x00 || JCS bytes), as
//   base64url without padding: exactly 43 characters (32 bytes). The label and
//   zero byte separate this use of the key from any other (P-ND-01)
//
// Sealing uses the ring's current key. Verification, in order: (1) parse
// strictly; (2) the kid is in the ring; (3) the MAC decodes to 32 bytes and
// re-encodes to the same 43 characters; (4) recompute; (5) compare with
// timingSafeEqual. Any failure is seal_failed, and (1) to (3) are decided
// before any MAC is computed.
//
// The ring comes from P9's loadSealKeys (U2's seed-key shape, each key exactly
// 256 bits). loadSealKeyRing checks what P9 does not: every id matches the
// kid pattern; ids are unique; current is among them. Any failure stops
// start-up. P9's ids are KeyId (^[a-z0-9][a-z0-9-]*$, up to 32), so the ids
// that can load are those both accept: ^[a-z0-9][a-z0-9-]{0,15}$ (Q-CG-AE-1).
import { createHmac, timingSafeEqual } from 'node:crypto';

export const SEAL_LABEL = 'soorma.envelope-seal.v1';
const KID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,15}$/;
const SEAL = /^v1\.([A-Za-z0-9][A-Za-z0-9_-]{0,15})\.([A-Za-z0-9_-]{43})$/;
const KEY_BYTES = 32;
const MAC_BYTES = 32;

export class SealKeyRingError extends Error {
  readonly problems: readonly string[];

  constructor(problems: readonly string[]) {
    super(`seal key ring refused (${problems.length}):\n- ${problems.join('\n- ')}`);
    this.name = 'SealKeyRingError';
    this.problems = problems;
  }
}

/** An environment's seal keys, as P9's loadSealKeys returns them. */
export interface SealKeyInput {
  readonly current: string;
  readonly keys: readonly { readonly id: string; readonly key: Buffer }[];
}

export interface SealKeyRing {
  readonly current: string;
  readonly ids: readonly string[];
  key(id: string): Buffer | undefined;
}

/** Checks and freezes the ring. Throws SealKeyRingError: start-up stops. */
export function loadSealKeyRing(input: SealKeyInput): SealKeyRing {
  const problems: string[] = [];
  const keys = new Map<string, Buffer>();
  for (const { id, key } of input.keys) {
    if (!KID.test(id)) problems.push(`seal key id ${JSON.stringify(id)} is not a valid kid`);
    if (keys.has(id)) problems.push(`seal key id ${id} appears twice`);
    if (key.length !== KEY_BYTES) problems.push(`seal key ${id} is not 256 bits`);
    keys.set(id, Buffer.from(key));
  }
  if (!keys.has(input.current)) problems.push('the current seal key is not in the ring');
  if (problems.length > 0) throw new SealKeyRingError(problems);
  const ids = Object.freeze([...keys.keys()]);
  return Object.freeze({
    current: input.current,
    ids,
    key: (id: string): Buffer | undefined => keys.get(id),
  });
}

export interface Sealer {
  /** The seal of a stamped envelope's JCS bytes, with the current key. */
  seal(jcsBytes: Buffer): string;
  /** Whether `seal` is this ring's seal over `jcsBytes`. Never throws. */
  verify(seal: unknown, jcsBytes: Buffer): boolean;
}

function mac(key: Buffer, jcsBytes: Buffer): Buffer {
  return createHmac('sha256', key)
    .update(SEAL_LABEL, 'utf8')
    .update(Buffer.of(0))
    .update(jcsBytes)
    .digest();
}

export function createSealer(ring: SealKeyRing): Sealer {
  const currentKey = ring.key(ring.current);
  if (!currentKey) throw new SealKeyRingError(['the current seal key is not in the ring']);
  return Object.freeze({
    seal(jcsBytes: Buffer): string {
      return `v1.${ring.current}.${mac(currentKey, jcsBytes).toString('base64url')}`;
    },
    verify(seal: unknown, jcsBytes: Buffer): boolean {
      if (typeof seal !== 'string') return false;
      const parsed = SEAL.exec(seal);
      if (!parsed) return false;
      const key = ring.key(parsed[1]!);
      if (!key) return false;
      const encoded = parsed[2]!;
      const presented = Buffer.from(encoded, 'base64url');
      if (presented.length !== MAC_BYTES || presented.toString('base64url') !== encoded)
        return false;
      return timingSafeEqual(mac(key, jcsBytes), presented);
    },
  });
}

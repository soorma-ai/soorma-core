// SPDX-License-Identifier: FSL-1.1-ALv2
// Fixtures for P2's tests (the narrative's Common Fixtures, construction
// pass). Every key here is fixed test material, never a production secret.
import { canonicalize } from '@soorma/jcs';
import { createSealer, loadSealKeyRing, type Sealer, type Scope } from '../src/index.ts';

/** 32 bytes counting up from `start`. */
export const testKey = (start: number): Buffer =>
  Buffer.from(Array.from({ length: 32 }, (_, i) => (start + i) & 0xff));

export const E: Scope = { organization: 'o1', project: 'p1', environment: 'e' };
export const E2: Scope = { organization: 'o1', project: 'p1', environment: 'e2' };

/** ring(E) and ring(E2): { current: k1, keys: [k1] }, different keys. */
export const ringE = loadSealKeyRing({ current: 'k1', keys: [{ id: 'k1', key: testKey(0x60) }] });
export const ringE2 = loadSealKeyRing({ current: 'k1', keys: [{ id: 'k1', key: testKey(0x90) }] });
export const sealerE: Sealer = createSealer(ringE);
export const sealerE2: Sealer = createSealer(ringE2);

export const TRACEPARENT = '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01';
export const TRACEPARENT_1 = '00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01';

export function draft(extra: Record<string, unknown> = {}): Record<string, unknown> {
  return { clientContractVersion: '0.1.0', traceContext: { traceparent: TRACEPARENT }, ...extra };
}

/** An envelope as admission(E) would stamp it for agent X's first hop. */
export function envelope(
  chain: string[] = ['a'],
  extra: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    envelopeVersion: 1,
    scope: { ...E },
    originMode: 'autonomous',
    actorChain: chain.map((agent) => ({ agent, instance: `${agent}-i` })),
    traceContext: { traceparent: TRACEPARENT },
    ...extra,
  };
}

/** sealed(env, ...): an envelope and its seal under a ring's current key. */
export function sealed(
  env: Record<string, unknown>,
  sealer: Sealer = sealerE,
): { envelope: Record<string, unknown>; seal: string } {
  return { envelope: env, seal: sealer.seal(canonicalize(env).bytes) };
}

/** An unknown field whose value pads an envelope's JCS form to `size` bytes. */
export function padTo(env: Record<string, unknown>, size: number): Record<string, unknown> {
  const base = canonicalize({ ...env, 'x-pad': '' }).bytes.length;
  return { ...env, 'x-pad': 'p'.repeat(size - base) };
}

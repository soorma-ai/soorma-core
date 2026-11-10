// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Check-order step 8: chain depth (U3 BR-CD-01, 02; D-AE-13; PF FR-006, O7).
// The new chain is the forwarded chain plus this hop, or one entry with no
// inbound. Over maxChainDepth (32) it is chain_too_deep, never truncated. It
// runs before origin and authority, so a loop is refused with no read.
import { ok, refuse, type Result } from './refusal.ts';

/** maxChainDepth for envelope v1 (U1 D-WC-05; pre-release statement 7). */
export const MAX_CHAIN_DEPTH = 32;

export function checkChainDepth(forwardedLength: number): Result<number> {
  const length = forwardedLength + 1;
  return length > MAX_CHAIN_DEPTH ? refuse('chain_too_deep', 'chain_depth') : ok(length);
}

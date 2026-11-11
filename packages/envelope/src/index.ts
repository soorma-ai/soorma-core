// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/envelope (P2): the envelope perimeter, check-order steps 5 to 8 and
// 10; the seal and its key ring (U3; BR-VR, BR-DV, BR-FX, BR-CD, BR-ST).
//
// No surface imports this package: a surface calls the one entry point in
// @soorma/authority, which runs steps 5 to 10 in order (D-AE-04). Its
// functions are exported for that entry point and for their own tests.
// Framework-free (NP-05).
export { checkChainDepth, MAX_CHAIN_DEPTH } from './chain.ts';
export { copyJson } from './copy.ts';
export {
  createDraftValidator,
  MAX_ERRORS,
  STAMPED_FIELDS,
  type DraftValidator,
  type ValidDraft,
} from './draft.ts';
export {
  ENVELOPE_BOUND,
  verifyInbound,
  type ActorReference,
  type Scope,
  type VerifiedInbound,
} from './inbound.ts';
export {
  isObject,
  ok,
  own,
  refuse,
  type FieldError,
  type Refusal,
  type RefusalCode,
  type RefusalReason,
  type Result,
} from './refusal.ts';
export {
  createSealer,
  loadSealKeyRing,
  SEAL_LABEL,
  SealKeyRingError,
  type SealKeyInput,
  type SealKeyRing,
  type Sealer,
} from './seal.ts';
export { stamp, type Stamped, type StampInput } from './stamp.ts';
export { checkVersion, CONTRACT_VERSION_HEADER } from './version.ts';

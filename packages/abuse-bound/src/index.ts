// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/abuse-bound (P8): the abuse bound over the attempt-slot table, and
// the Failed Attempt writer; and, since U6, the generic core both are built on
// (SlotBound, BatchWriter; NP-AC-07).
export {
  AbuseBound,
  BACKOFF_CAP_SECONDS,
  BACKOFF_FROM_FAILURE,
  MAX_LIVE_ENTRIES,
  retryAfterSeconds,
  SLOT_COUNT,
  slotOf,
  WINDOW_MS,
  type Admission,
  type Reservation,
} from './abuse-bound.ts';
export {
  BATCH_SIZE,
  FailedAttemptWriter,
  FLUSH_INTERVAL_MS,
  QUEUE_LIMIT,
  type FailedAttempt,
  type Surface,
  type WriterOptions,
} from './failed-attempt-writer.ts';
export { retryAfterFor, SlotBound, slotOfKey, type SlotLimits } from './slot-bound.ts';
export { BatchWriter } from './batch-writer.ts';

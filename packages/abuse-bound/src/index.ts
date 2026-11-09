// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/abuse-bound (P8): the abuse bound over the attempt-slot table, and
// the Failed Attempt writer.
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

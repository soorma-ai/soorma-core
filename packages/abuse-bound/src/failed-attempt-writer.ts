// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The Failed Attempt writer (P-11; NFR-OI-21; D-OI-27): records are written
// off the response path, so the response never waits for them and their
// timing cannot say whether the principal exists (BR-RF-03).
//
// Built on P8's generic BatchWriter since U6 (batch-writer.ts; NP-AC-07,
// D-CG-AC-05): every export, signature, and result here is unchanged.
//
// A bounded in-process queue of 10,000; batches of at most 100 rows, every
// 250 ms or as soon as 100 are waiting. A full queue drops the record and
// reports the drop. A failed batch is dropped and reported too. Shutdown
// flushes. A crash may lose what is queued: accepted, because the bound lives
// in the counters, not in these records.
//
// Only records for an existing principal reach it (D-OI-16), and nothing
// presented is in them: no K, P proof, or enrollment material.
import type { Queryable } from '@soorma/service-kit';
import {
  BATCH_SIZE,
  BatchWriter,
  FLUSH_INTERVAL_MS,
  QUEUE_LIMIT,
  type WriterOptions,
} from './batch-writer.ts';
import { SQL } from './sql.ts';

export { BATCH_SIZE, FLUSH_INTERVAL_MS, QUEUE_LIMIT, type WriterOptions };

export type Surface = 'authenticate' | 'firstAuthenticate' | 'changeMaterial';

export interface FailedAttempt {
  organization: string;
  principal: string;
  surface: Surface;
  at: Date;
  refusedByBound: boolean;
}

export class FailedAttemptWriter extends BatchWriter<FailedAttempt> {
  constructor(store: Queryable, options: WriterOptions = {}) {
    super(
      store,
      SQL.insertFailedAttempts,
      (batch) => [
        batch.map((a) => a.organization),
        batch.map((a) => a.principal),
        batch.map((a) => a.surface),
        batch.map((a) => a.at.toISOString()),
        batch.map((a) => a.refusedByBound),
      ],
      options,
    );
  }
}

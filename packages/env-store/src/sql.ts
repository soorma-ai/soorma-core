// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The environment store's own statements (D-CG-OI-04; NFR-EHA-13). Each module
// over it (P4, P5, P7) keeps its statements in its own src/sql.ts.
import { statement } from '@soorma/service-kit';

const sql = statement;

export const SQL = {
  /** Asserted at S2's start-up (NFR-EHA-10). */
  synchronousCommit: sql('SHOW synchronous_commit'),
};

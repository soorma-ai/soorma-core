// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The start-up self-check (NP-ET-05; D-CG-ET-10; the user's condition): S4
// refuses to start unless this runtime carries payload numbers by their
// source text. **No fallback**: a runtime without JSON.rawJSON,
// JSON.isRawJSON, and the reviver's source-text context does not run S4,
// because a parse that converts numbers would deliver a payload other than
// the one published.
import { ConfigurationError } from '@soorma/config';
import { hasRawJson, parseRawNumbers } from '@soorma/jcs';

/** An integer above 2^53: a double cannot hold it, so only its source text survives. */
const PROBE = '[12345678901234567890]';

/** Throws ConfigurationError unless the runtime round-trips a number by its source text. */
export function checkRawJson(): void {
  if (!hasRawJson())
    throw new ConfigurationError([
      'this runtime has no JSON.rawJSON and JSON.isRawJSON: S4 cannot carry payload numbers as written',
    ]);
  let written: string;
  try {
    written = JSON.stringify(parseRawNumbers(PROBE));
  } catch {
    written = '';
  }
  if (written !== PROBE)
    throw new ConfigurationError([
      'this runtime does not round-trip a number by its source text: S4 cannot carry payload numbers as written',
    ]);
}

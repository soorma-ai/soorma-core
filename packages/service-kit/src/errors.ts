// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The organization level's failure kinds. The service maps each to its Problem.

/** A dependency (the store, the hashing budget) cannot serve now: 503, fail closed. */
export class UnavailableError extends Error {
  readonly retryAfterSeconds: number;

  constructor(reason: string, retryAfterSeconds = 1) {
    super(reason);
    this.name = 'UnavailableError';
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

/** Key material is missing or malformed at start-up: start-up stops (BR-CFG-08). */
export class KeyMaterialError extends Error {
  readonly problems: readonly string[];

  constructor(problems: readonly string[]) {
    super(`key material refused (${problems.length}):\n- ${problems.join('\n- ')}`);
    this.name = 'KeyMaterialError';
    this.problems = problems;
  }
}

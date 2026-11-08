// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Lint fixture (TC-WC-041): one deliberate floating promise. The normal lint run
// ignores this directory (eslint.config.js); tools/test/lint.test.ts lints this
// file explicitly and expects exactly one @typescript-eslint/no-floating-promises
// error.

async function save(): Promise<void> {
  await Promise.resolve();
}

export function handler(): void {
  save();
}

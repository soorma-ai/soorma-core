// SPDX-License-Identifier: FSL-1.1-ALv2
// pnpm stack:up's minimum versions (Q-CG-4 B: volume subpaths).
import { describe, expect, it } from 'vitest';
import { atLeast, parseVersion, versionProblems } from '../local/scripts/stack-up.ts';

describe('stack:up refuses a Docker too old for volume subpaths', () => {
  it('reads the versions Docker and Compose print', () => {
    expect(parseVersion('28.0.4')).toEqual([28, 0, 4]);
    expect(parseVersion('v2.38.2')).toEqual([2, 38, 2]);
    expect(parseVersion('5.1.4-desktop.1')).toEqual([5, 1, 4]);
    expect(parseVersion('')).toBeUndefined();
    expect(atLeast([2, 26, 0], [2, 26, 0])).toBe(true);
    expect(atLeast([2, 25, 9], [2, 26, 0])).toBe(false);
    expect(atLeast([5, 1, 4], [2, 26, 0])).toBe(true);
  });

  it('accepts Engine 26 and Compose 2.26.0, and refuses older with a message', () => {
    expect(versionProblems('28.0.4', '2.38.2')).toEqual([]);
    expect(versionProblems('26.0.0', '2.26.0')).toEqual([]);
    expect(versionProblems('29.5.3', '5.1.4')).toEqual([]);
    expect(versionProblems('25.0.5', '2.38.2')).toEqual([
      'Docker Engine 25.0.5 is too old: the stack needs 26.0.0 or later (volume subpaths).',
    ]);
    expect(versionProblems('28.0.4', '2.25.0')).toEqual([
      'Docker Compose 2.25.0 is too old: the stack needs 2.26.0 or later (it passes volume subpaths to the Engine).',
    ]);
    expect(versionProblems('', '')).toHaveLength(2);
  });
});

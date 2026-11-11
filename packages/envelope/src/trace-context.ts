// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The trace-context rules a schema cannot express (U1 BR-TC; U3 D-AE-17;
// contract/conventions/envelope.md, "Rules checked in code"). Run after the
// schema has checked form. Values are validated, never interpreted.
//
// - A traceparent version of ff is invalid
// - An all-zero trace id, or an all-zero parent id, is invalid
// - tracestate has at most 32 list members (empty members are not counted)
// - Each tracestate key follows W3C key syntax:
//     simple-key       = lcalpha 0*255( lcalpha / DIGIT / "_" / "-" / "*" / "/" )
//     multi-tenant-key = tenant-id "@" system-id
//     tenant-id        = ( lcalpha / DIGIT ) 0*240( lcalpha / DIGIT / "_" / "-" / "*" / "/" )
//     system-id        = lcalpha 0*13( lcalpha / DIGIT / "_" / "-" / "*" / "/" )
import type { FieldError } from './refusal.ts';

export const TRACEPARENT_POINTER = '/traceContext/traceparent';
export const TRACESTATE_POINTER = '/traceContext/tracestate';
const MAX_TRACESTATE_MEMBERS = 32;

const KEY = /^(?:[a-z][a-z0-9_\-*/]{0,255}|[a-z0-9][a-z0-9_\-*/]{0,240}@[a-z][a-z0-9_\-*/]{0,13})$/;

export function traceparentProblems(traceparent: string): FieldError[] {
  const [version, traceId, parentId] = traceparent.split('-');
  const problems: string[] = [];
  if (version === 'ff') problems.push('version ff is invalid');
  if (traceId !== undefined && /^0+$/.test(traceId)) problems.push('the trace id is all zero');
  if (parentId !== undefined && /^0+$/.test(parentId)) problems.push('the parent id is all zero');
  return problems.length > 0 ? [{ pointer: TRACEPARENT_POINTER, detail: problems.join('; ') }] : [];
}

export function tracestateProblems(tracestate: string): FieldError[] {
  const members = tracestate
    .split(',')
    .map((m) => m.trim())
    .filter((m) => m.length > 0);
  const problems: string[] = [];
  if (members.length > MAX_TRACESTATE_MEMBERS)
    problems.push(`more than ${MAX_TRACESTATE_MEMBERS} list members`);
  if (members.some((m) => !KEY.test(m.slice(0, Math.max(0, m.indexOf('='))))))
    problems.push('a key does not follow W3C key syntax');
  return problems.length > 0 ? [{ pointer: TRACESTATE_POINTER, detail: problems.join('; ') }] : [];
}

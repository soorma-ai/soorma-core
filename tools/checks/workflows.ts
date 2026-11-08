// SPDX-License-Identifier: FSL-1.1-ALv2
//
// NFR-WC-20: every GitHub Action is pinned by a full commit SHA; workflow
// permissions default to `contents: read`; a job that widens them carries its
// reason in a comment on its `permissions` key.
import { isMap, isPair, isScalar, parseDocument, type Pair, type YAMLMap } from 'yaml';
import type { Finding } from './workspace.ts';

const PINNED = /@[0-9a-f]{40}$/;

function keyOf(pair: Pair): string {
  return isScalar(pair.key) ? String(pair.key.value) : '';
}

function get(map: YAMLMap, key: string): Pair | undefined {
  return map.items.find((p) => isPair(p) && keyOf(p) === key);
}

function isReadOnly(value: unknown): boolean {
  return JSON.stringify(value) === JSON.stringify({ contents: 'read' });
}

function hasComment(pair: Pair): boolean {
  const k = pair.key as { commentBefore?: string | null; comment?: string | null } | null;
  const v = pair.value as { commentBefore?: string | null; comment?: string | null } | null;
  return Boolean(k?.commentBefore || k?.comment || v?.commentBefore || v?.comment);
}

export function workflowFindings(files: { path: string; text: string }[]): Finding[] {
  const findings: Finding[] = [];
  for (const { path, text } of files) {
    const add = (where: string, message: string): void => {
      findings.push({ check: 'workflows', location: `${path}: ${where}`, message });
    };
    const doc = parseDocument(text);
    const data = doc.toJS() as {
      permissions?: unknown;
      jobs?: Record<string, { uses?: string; steps?: { uses?: string }[] }>;
    };

    if (!isReadOnly(data.permissions))
      add('permissions', 'the workflow default must be exactly `contents: read`');

    for (const [jobId, job] of Object.entries(data.jobs ?? {})) {
      const uses = [job.uses, ...(job.steps ?? []).map((s) => s.uses)].filter(
        (u): u is string => typeof u === 'string',
      );
      for (const u of uses) {
        if (!u.startsWith('./') && !PINNED.test(u))
          add(`jobs.${jobId}`, `\`uses: ${u}\` is not pinned by a 40-character commit SHA`);
      }
    }

    const jobs = isMap(doc.contents) ? get(doc.contents, 'jobs') : undefined;
    if (jobs && isMap(jobs.value)) {
      for (const jobPair of jobs.value.items) {
        if (!isPair(jobPair) || !isMap(jobPair.value)) continue;
        const permissions = get(jobPair.value, 'permissions');
        if (!permissions) continue;
        const value = (permissions.value as { toJSON?: () => unknown } | null)?.toJSON?.();
        // A comment above a map's first key is attached to the map itself.
        const leadingComment =
          jobPair.value.items[0] === permissions && Boolean(jobPair.value.commentBefore);
        if (!isReadOnly(value) && !hasComment(permissions) && !leadingComment) {
          add(
            `jobs.${keyOf(jobPair)}.permissions`,
            'widens permissions without a recorded reason (a comment on `permissions`)',
          );
        }
      }
    }
  }
  return findings;
}

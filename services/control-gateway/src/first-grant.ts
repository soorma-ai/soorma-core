// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The configured first grant (BR-FG-01 to 06; NP-EHA-08; D-EHA-07): at S2's
// start-up, E's configured first Admin receives one configuration grant of
// grant:human and human:manage, if E holds none for them. The store's partial
// unique index makes it once: concurrent start-ups write at most one grant and
// one attribution record, and the one that loses writes nothing. No call to
// S1 and no enrollment material at E (BR-FG-04). If it cannot be written, S2
// does not start (BR-FG-05).
import { recordAttribution } from '@soorma/attribution';
import { newRecordId, withTransaction } from '@soorma/env-store';
import { applyFirstGrant } from '@soorma/registry';
import type { Runtime } from './runtime.ts';
import { FIRST_ADMIN_PERMISSIONS } from './settings.ts';

export async function applyConfiguredFirstGrant(rt: Runtime, firstAdmin: string): Promise<boolean> {
  const now = rt.clock.now();
  const applied = await withTransaction(rt.store, async (tx) => {
    const grant = await applyFirstGrant(tx, {
      id: newRecordId(),
      environment: rt.environment,
      principal: firstAdmin,
      permissions: FIRST_ADMIN_PERMISSIONS,
      grantedAt: now,
    });
    if (!grant) return false;
    await recordAttribution(tx, {
      id: newRecordId(),
      recordedAt: now,
      environment: rt.environment,
      operation: 'configureFirstGrant',
      actor: { kind: 'configuration' },
      target: { kind: 'grant', id: grant.id },
    });
    return true;
  });
  if (applied)
    rt.log.event('first_grant.applied', undefined, { pseudonym: rt.pseudonym(firstAdmin) });
  return applied;
}

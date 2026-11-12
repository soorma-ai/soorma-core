// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P6's agent half (U6 D-AC-08, 19, 20, 34; NFR Design NP-AC-08; BR-BS-01 to
// 03): the identity-resolution seam over the registration secret.
//
// 1. The material's type is its typed prefix: only `soorma_rs_` (D-AC-04)
// 2. The value is parsed by U5's parseRegistrationSecret (one encoding per
//    value), before any store read
// 3. One read: the secret record its value names, by id, in E, and whether
//    the claimed agent exists (for the reason only). It never iterates a
//    registration's secrets (U5's obligation)
// 4. The comparison is U5's registrationSecretMatches, in constant time, and
//    it always runs: against the stored digest, or against a fixed 32-byte
//    dummy when there is no record, so the work after the read does not
//    depend on whether a record exists (D-AC-34)
//
// It decides identity only (D-AC-20): the registration's state, revocation,
// the attempt bound, and what the credential asserts are S3's, behind no seam.
// Every rejection is `{ resolved: false }`; its reason goes only to
// `onRejected`, which S3 wires to its security log and the failed-attempt
// writer. Nothing logs the value, its id, or its digest. A store failure
// propagates (S3 answers `unavailable`).
import type {
  AgentIdentityResolver,
  AgentMaterialType,
  AgentRegistrationReference,
  AgentResolution,
} from '@soorma/identity-resolution-seam';
import {
  parseRegistrationSecret,
  REGISTRATION_SECRET_PREFIX,
  registrationSecretMatches,
} from '@soorma/registry';
import { asSecretText, type Queryable } from '@soorma/service-kit';
import { SQL } from './sql.ts';

/** Why a resolution was rejected: for the security log only, never a response. */
export type AgentRejection =
  | 'unsupported_material'
  | 'malformed_secret'
  | 'unknown_registration'
  | 'unknown_secret'
  | 'secret_not_active'
  | 'secret_mismatch';

export interface AgentIdentityOptions {
  /** The environment store (S3 connects as soorma_env_data). */
  readonly store: Queryable;
  /** Told why a resolution was rejected. */
  readonly onRejected?: (reason: AgentRejection) => void;
}

/** Compared against when no record exists, so the comparison always runs. */
const NO_DIGEST = Buffer.alloc(32);

export function createAgentIdentityResolver(options: AgentIdentityOptions): AgentIdentityResolver {
  const { store } = options;
  const rejected = (reason: AgentRejection): AgentResolution => {
    options.onRejected?.(reason);
    return { resolved: false };
  };

  return Object.freeze({
    async resolve(
      type: AgentMaterialType,
      claimed: AgentRegistrationReference,
      material: string,
    ): Promise<AgentResolution> {
      if (type !== 'registrationSecret' || !material.startsWith(REGISTRATION_SECRET_PREFIX))
        return rejected('unsupported_material');
      const parsed = parseRegistrationSecret(asSecretText(material));
      if (parsed.kind !== 'parsed') return rejected('malformed_secret');
      const { organization, project, environment } = claimed.environment;
      const [row] = await store.query<{
        agent_exists: boolean;
        registration: string | null;
        state: string | null;
        digest: Buffer | null;
      }>(SQL.secretForBootstrap, [organization, project, environment, claimed.agent, parsed.id]);
      const matches = registrationSecretMatches(parsed.secretBytes, row?.digest ?? NO_DIGEST);
      if (!row?.agent_exists) return rejected('unknown_registration');
      if (row.registration === null || row.registration !== claimed.agent)
        return rejected('unknown_secret');
      if (row.state !== 'active') return rejected('secret_not_active');
      if (!matches) return rejected('secret_mismatch');
      return { resolved: true, registration: claimed, secretId: parsed.id };
    },
  });
}

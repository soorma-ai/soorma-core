// SPDX-License-Identifier: Apache-2.0
//
// The identity-resolution seam, human half (PF §12 v1.3; ID FR-027; BR-SEAM).
// Type definitions only: no code, no configuration selection, no published
// interface (BR-SEAM-03).
//
// It takes a material type, a principal reference, and the material, and
// returns a human principal reference or a rejection (BR-SEAM-01). It decides
// identity only: the human record and its state, enrollment single use, the K
// policy, the P requirement, and sign-in issuance stay behind no seam
// (BR-SEAM-02). External types (class X) are absent in M1.

/** A human principal, named with its organization. */
export interface HumanPrincipalReference {
  organization: string;
  principal: string;
}

/** The material each type takes, as presented. */
export interface PresentedMaterial {
  /** K, the secret. */
  K: string;
  /** A proof of P, by authenticator type. */
  P: { type: string; code: string };
  /** Single-use enrollment material. */
  enrollment: string;
}

export type MaterialType = keyof PresentedMaterial;

/** Identity, or a rejection. A rejection never says why. */
export type Resolution =
  | {
      resolved: true;
      principal: HumanPrincipalReference;
      /**
       * The material record that verified, so the caller can apply what stays
       * behind no seam: single use, state changes, the accepted P step.
       */
      materialId: string;
      /** For P: the step the code matched; the caller accepts it at most once. */
      acceptedStep?: number;
    }
  | { resolved: false };

export interface IdentityResolver {
  resolve<T extends MaterialType>(
    type: T,
    reference: HumanPrincipalReference,
    material: PresentedMaterial[T],
  ): Promise<Resolution>;
}

// The agent half (U6), beside the human half above, which is unchanged.
export type {
  AgentIdentityResolver,
  AgentMaterialType,
  AgentRegistrationReference,
  AgentResolution,
} from './agent.ts';

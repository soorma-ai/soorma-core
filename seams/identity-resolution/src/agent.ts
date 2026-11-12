// SPDX-License-Identifier: Apache-2.0
//
// The identity-resolution seam, agent half (PF §12 v1.3; FR-009, FR-026;
// M1-FR-13; U6 D-AC-20; NFR Design NP-AC-08). Type definitions only: no code,
// no configuration selection, no published interface (BR-SEAM-03).
//
// It takes a material type, the registration the material claims, and the
// material, and returns the registration it is bound to, or a rejection that
// never says why. It decides identity only: the registration's state,
// revocation, the attempt bound, and what the credential asserts stay in core,
// behind no seam (PF §12 containment), as the human half's lifecycle does.
// M1 accepts the locally verified registration secret only.

/** The material types the agent half accepts: the registration secret only, in M1. */
export type AgentMaterialType = 'registrationSecret';

/** A logical agent's registration: an agent in one environment. */
export interface AgentRegistrationReference {
  environment: { organization: string; project: string; environment: string };
  agent: string;
}

/** Identity, or a rejection. A rejection never says why. */
export type AgentResolution =
  | {
      resolved: true;
      registration: AgentRegistrationReference;
      /** The secret record that verified, so core can record which one bootstrapped. */
      secretId: string;
    }
  | { resolved: false };

export interface AgentIdentityResolver {
  resolve(
    type: AgentMaterialType,
    claimed: AgentRegistrationReference,
    material: string,
  ): Promise<AgentResolution>;
}

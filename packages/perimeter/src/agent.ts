// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P1's agent checks (U6 D-AC-10, 27; BR-PR-AC-03, 04; NFR Design NP-AC-11):
// the presenter at S3's renewal (and, from U7, at S4), and `checkAgentRequest`,
// O1, O2, O4, then O3, returning the Checked Agent Context (U3 D-AE-08: scope,
// agent, instance; with the credential's cid).
//
// - Exactly one `Authorization: Bearer soorma_ac_…`, counted on the raw header
//   list, and no `Soorma-Delegation`. A human credential (`soorma_ec_`,
//   `soorma_si_`), a delegation credential, an unknown prefix, or two
//   credentials are refused **by kind, without verifying** (ID §8b; FR-023)
// - The verification and the revocation read are the caller's callbacks (P5's
//   verifier over the agent key ring; the direct source at S3, the cache at
//   S4), as U4's SignInPerimeter takes its key source and status, so P1 gains
//   no dependency on P5. One implementation, run independently by each surface
//   (O10)
// - A revocation read that cannot answer throws (UnavailableError): the
//   request is denied as unavailable, never passed
import { asSecretText, type SecretText } from '@soorma/service-kit';
import { presentedCredential } from './presenter.ts';

/** The prefix of an agent credential (credentials.md). */
export const AGENT_CREDENTIAL_PREFIX = 'soorma_ac_';

/** The presented agent credential, as a secret, or undefined: refused by kind. */
export function presentedAgentCredential(rawHeaders: readonly string[]): SecretText | undefined {
  const credential = presentedCredential(rawHeaders, AGENT_CREDENTIAL_PREFIX);
  return credential === undefined ? undefined : asSecretText(credential);
}

/** What a verified agent credential asserts (U3 D-AE-08), with its lineage. */
export interface CheckedAgentContext {
  readonly scope: { organization: string; project: string; environment: string };
  readonly agent: string;
  readonly instance: string;
  readonly cid: string;
}

/** O1, O2, O4: the caller's verification of the token with E's agent key ring. */
export type AgentVerification =
  | { readonly ok: true; readonly context: CheckedAgentContext }
  | {
      readonly ok: false;
      readonly code: 'credential_refused' | 'credential_expired';
      readonly reason: string;
    };

export interface AgentRequestChecks {
  verify(token: SecretText): Promise<AgentVerification>;
  /** O3 at both granularities. Throws when it cannot answer: the request is unavailable. */
  revocation(context: CheckedAgentContext): Promise<'revoked' | 'not_revoked'>;
}

export type AgentCheck =
  | { readonly accepted: true; readonly context: CheckedAgentContext }
  | {
      readonly accepted: false;
      readonly code: 'credential_refused' | 'credential_expired';
      /** For the security log only, never a response. */
      readonly reason: string;
    };

/** The presenter, O1, O2, O4, then O3 (D-AC-27). */
export async function checkAgentRequest(
  rawHeaders: readonly string[],
  checks: AgentRequestChecks,
): Promise<AgentCheck> {
  // The presented value is tested while it is a plain header string, then
  // becomes a secret (NP-EHA-14; the compare check).
  const presented = presentedCredential(rawHeaders, AGENT_CREDENTIAL_PREFIX);
  if (presented === undefined)
    return { accepted: false, code: 'credential_refused', reason: 'presenter' };
  const verified = await checks.verify(asSecretText(presented));
  if (!verified.ok) return { accepted: false, code: verified.code, reason: verified.reason };
  if ((await checks.revocation(verified.context)) === 'revoked')
    return { accepted: false, code: 'credential_refused', reason: 'credential_revoked' };
  return { accepted: true, context: verified.context };
}

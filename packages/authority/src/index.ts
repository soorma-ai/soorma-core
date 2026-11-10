// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/authority (P3): step 9 (origin and effective authority), and the
// one entry point a surface imports, createEnvelopeAdmission(dependencies)
// .admit(request), which runs check-order steps 5 to 10 in order (U3 D-AE-04).
//
// Effective authority is computed in one place, evaluateAgent (I5). P3
// depends on P2 and the policy-decision seam, never on P1 or P11 (NP-05;
// D-AE-25): P11 arrives as an injected factory. Framework-free.
export {
  createEnvelopeAdmission,
  type AdmissionDependencies,
  type AdmissionResult,
  type Admitted,
  type CheckedAgentContext,
  type EnvelopeAdmission,
  type EnvelopeRefusedEvent,
  type EnvelopeRequest,
  type Refused,
  type SecurityLog,
} from './admission.ts';
export {
  cacheKey,
  createCachingAgentFacts,
  requestGrantSource,
  requestSnapshot,
  type AgentFacts,
  type AgentFactsSource,
  type CacheOptions,
  type Clock,
  type GrantSource,
  type RegistrationView,
  type RequestSnapshot,
} from './agent-facts.ts';
export {
  evaluateAgent,
  type Evaluation,
  type EvaluationInput,
  type EvaluationReason,
} from './evaluate.ts';
export { HUMAN_ONLY_PERMISSIONS } from './human-only.ts';
export { resolveOrigin, type Origin } from './origin.ts';

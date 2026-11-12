// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/perimeter (P1): classifies and verifies the presenter at S1 (and, since
// U6, the agent presenter and checkAgentRequest at S3 and S4), and
// holds the one Problem table and its emission for every edge (U3 D-AE-06).
// The table itself moved to @soorma/service-kit (U4 NP-EHA-15) and is
// re-exported here, so every surface still emits through P1 (D-EHA-21).
// The shared Problem assertion is the test-only `@soorma/perimeter/testing`.
export {
  CREDENTIAL_HEADERS,
  ENVIRONMENT_CREDENTIAL_PREFIX,
  presentedCredential,
  presentedEnvironmentCredential,
  presentedCredentialHeaders,
  presentedSignIn,
  rawHeaderValues,
  SignInPerimeter,
  type CredentialHeader,
  type SignInCheck,
  type SignInPerimeterOptions,
} from './presenter.ts';
export {
  AGENT_CREDENTIAL_PREFIX,
  checkAgentRequest,
  presentedAgentCredential,
  type AgentCheck,
  type AgentRequestChecks,
  type AgentRevocation,
  type AgentVerification,
  type CheckedAgentContext,
} from './agent.ts';
export {
  CONTRACT_VERSION,
  isProblemCode,
  PROBLEM_TABLE,
  ProblemError,
  problemBody,
  problemResponse,
  SUPPORTED_VERSIONS,
  type FieldError,
  type ProblemCode,
  type ProblemResponse,
  type Refusal,
} from '@soorma/service-kit';

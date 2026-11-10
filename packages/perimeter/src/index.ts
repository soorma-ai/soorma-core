// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/perimeter (P1): classifies and verifies the presenter at S1, and
// holds the one Problem table and its emission for every edge (U3 D-AE-06).
// The shared Problem assertion is the test-only `@soorma/perimeter/testing`.
export {
  CREDENTIAL_HEADERS,
  presentedCredentialHeaders,
  presentedSignIn,
  rawHeaderValues,
  SignInPerimeter,
  type CredentialHeader,
  type SignInCheck,
} from './presenter.ts';
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
} from './problems.ts';

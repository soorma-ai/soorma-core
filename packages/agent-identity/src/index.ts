// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/agent-identity (P6's agent half; U6 D-AC-08): the identity-resolution
// seam's agent half over the registration secret. S3 links it; S3 never links
// @soorma/identity-resolution (the human half, which depends on P10).
export {
  createAgentIdentityResolver,
  type AgentIdentityOptions,
  type AgentRejection,
} from './resolver.ts';

// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/agent-identity (P6's agent half; U6 D-AC-08): the identity-resolution
// seam's agent half over the registration secret. Its statement comes first
// (Group 3), so the store's privilege test runs it; the resolver is Group 5's.
export { SQL as AGENT_IDENTITY_SQL } from './sql.ts';

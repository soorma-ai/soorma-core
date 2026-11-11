<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# `@soorma/authority` (P3)

Step 9 of the check order, origin and effective authority, and **the one entry point a surface
imports** for an envelope-bearing request:

```ts
createEnvelopeAdmission(dependencies).admit(request);
```

**Effective authority is computed in one place**, `evaluateAgent` (invariant I5). No other
module, surface, or seam computes an intersection or a union of permission sets. The package
imports no framework, and does not depend on P1 or P11: P11 arrives as an injected factory.

## How S4 uses it (U7)

S4 builds the entry point **once per instance**, and calls `admit` **once per publish and per
subscribe**, after it has run steps 1 to 4 itself:

- step 1: the body-size limit
- steps 2 and 3: the credential's presentation, kind, verification, and expiry
- step 4: the environment and revocation

```ts
const facts = createCachingAgentFacts(agentFactsSource /* U5 */, {
  ttl: propagationBoundMs, // the one propagation bound; no second number
  clock,
});
const admission = createEnvelopeAdmission({
  acceptedVersions: SUPPORTED_VERSIONS,       // P1
  scope,                                      // this environment, from P9
  keyRing: loadSealKeyRing(loadSealKeys(...)), // P9, then P2; start-up stops on any problem
  facts,
  policyFactory: createPolicyDecision,        // P11
  humanGrants,                                // U4
  securityLog,                                // S4's JSON logger
});

const result = await admission.admit({
  body,                                       // the parsed JSON body
  contractVersionHeader,                      // every Soorma-Contract-Version value
  agent: { scope, agent, instance },          // the Checked Agent Context, from the credential
  required: ['event:publish'],                // or ['event:subscribe']
  requestId,
});
```

`admit` returns `{ admitted: { envelope, seal, outcome } }` or `{ refused: { code, errors?,
retryAfterSeconds? } }`. A refusal is never thrown.

- **Refused**: the result is P1's `Refusal` shape, so S4 passes it straight to
  `problemResponse`, and its edge tests run `assertProblem` on every Problem.
- **Admitted**: S4 publishes with the envelope and delivers the seal **beside** it. It writes the
  attribution record from `outcome`: the origin, whether re-broadening was load-bearing, and the
  chain.
- **An unexpected exception** propagates. S4's error handler answers `internal_error`.

Each refusal writes exactly one `envelope_refused` event to `securityLog`, with these fields: the
code, the internal reason, the request id, the environment, the agent, and the instance. The
event never carries the body, the seal, the forwarded envelope, or trace values.

## The ports other units fill

| Port                                         | Filled by                       | Rule                                                                                                                                                   |
| -------------------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `AgentFactsSource.load(environment, agents)` | U5, from P4, **with one query** | For each agent, its Registration View (`autonomyDeclared`, `reBroadeningDeclaration`) and standing set, or not found. A failure rejects the whole call |
| `humanGrants: GrantSource`                   | U4                              | A human's granted set: the union of its grants in the environment. Never cached                                                                        |
| `securityLog`                                | U7 (S4)                         | One event type, `envelope_refused`                                                                                                                     |

`HUMAN_ONLY_PERMISSIONS` is the single definition of the human-only class. U5's registration
check imports it; it never keeps a copy.

## The agent-facts cache

`createCachingAgentFacts` is the one caching decorator on the agent-facts port:

- The facts are read once, at the start of step 9, for the presenter and every distinct upstream
  agent. The read is all or nothing.
- Keys carry the organization, project, environment, and agent.
- The TTL is the propagation bound, measured from when the read was **issued**.
- It holds at most 4096 entries, evicting the least recently used.
- Failures and not-found results are never cached.
- Concurrent misses share one read.
- Humans bypass it.

**Standing note (NFR-AE-16)**: in M1, no operation changes a standing set, a re-broadening
declaration, or autonomy declared, or suspends or retires an agent. So this cache cannot serve
stale data in M1. **The unit that first adds such an operation must account for the cache's
staleness window**, which is up to the propagation bound, either by invalidating entries or by
accepting the window and stating it.

## Origin, while GAP-AE-001 is open

An `autonomous` origin, whether stamped or propagated, requires the presenter's own autonomy
declaration. An agent that has not declared autonomy is refused `forbidden`, including when it
forwards an autonomous envelope. This is the work-around for soorma-prd#30 (pre-release
statement 9). Allowing that case later would be additive.

## Benchmark

`pnpm bench:admit` measures steps 5 to 10 for a maximum-size forwarding draft with a warm cache
(TC-AE-040). It **reports**, and does not gate: Build and Test records p50 and p99 against the
2 ms target.

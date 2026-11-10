# Logical Components: U3 `authority-evaluation`

**Unit**: U3 `authority-evaluation` (soorma-core#6). Modules only: no deployable, listener,
store, or background worker. S4 (U7) hosts everything here
**Patterns**: [nfr-design-patterns.md](nfr-design-patterns.md)

---

## Packages

| Package | Licence | Responsibility | Exports | Depends on |
|---|---|---|---|---|
| `packages/jcs` (new) | FSL-1.1-ALv2 | RFC 8785, iterative (NP-03) | `canonicalize`, `CanonicalizationError` | nothing |
| `seams/policy-decision` | Apache-2.0, unpublished | The seam's types (BR-SEAM-01) | `PermissionId`, `PermissionSet`, `PrincipalRef`, `EnvironmentRef`, `PolicyDecision` | nothing |
| `packages/policy-decision` (P11) | FSL-1.1-ALv2 | The default: literal containment, deny by default, one environment (BR-SEAM-03) | `createPolicyDecision({ environment, grants })`, `GrantSource` | `seams/policy-decision` |
| `packages/envelope` (P2) | FSL-1.1-ALv2 | Steps 5 to 8 and 10: version, draft, forwarded context, chain depth, stamp; the sealer and key ring | `checkVersion`, `createDraftValidator`, `verifyInbound`, `checkChainDepth`, `stamp`, `loadSealKeyRing`, `createSealer` | `ajv`, `packages/jcs`, `contract` (the schema) |
| `packages/authority` (P3) | FSL-1.1-ALv2 | Step 9 and the entry point: origin, evaluation, the human-only class, agent facts and its cache | `createEnvelopeAdmission`, `resolveOrigin`, `evaluateAgent`, `HUMAN_ONLY_PERMISSIONS`, `AgentFactsSource`, `createCachingAgentFacts` | `packages/envelope`, `seams/policy-decision` |
| `packages/perimeter` (P1), changed | FSL-1.1-ALv2 | The Problem table, emission, and contract versions (BR-PE) | adds `problemResponse`, `ProblemCode`, `CONTRACT_VERSION`, `SUPPORTED_VERSIONS`; **test-only** `./testing` → `assertProblem` | unchanged, plus nothing new |
| `packages/org-identity` (P10), changed | FSL-1.1-ALv2 | `canonical.ts` becomes a wrapper over `packages/jcs` (NP-03) | unchanged | adds `packages/jcs` |
| `packages/config` (P9), changed | FSL-1.1-ALv2 | `sealKeys: { current, keys: [{ id, secret }] }` in the environment part of the tenancy schema, loaded through the seed keys' path (NP-02) | the loaded `sealKeys` | unchanged |
| `services/org-gateway` (S1), changed | FSL-1.1-ALv2 | Uses P1's emission; its `problems.ts` removed (BR-PE-05) | unchanged | P1 |

**No package imports NestJS** except S1 and P10, as before (Q4 A). **No surface imports P2.**
P3 does not import P1 or P11.

## The Entry Point at Run Time

**Naming**: D-AE-04's single entry point is `createEnvelopeAdmission(dependencies).admit(request)`. Functional Design, `component-methods.md` and the first #10 obligation called it `admitEnvelopeRequest`; they now use this form, each marked as a consistency fix from NFR Design (2026-11-10).

```text
S4 (U7), once per instance:
    sealKeys  = P9's environment loader: { current, keys: [{ id, key }] }  SecretReader.key(secret, true)
    keyRing   = loadSealKeyRing(sealKeys)                               start-up; stops on error
    facts     = createCachingAgentFacts(U5's AgentFactsSource,
                                        { ttl: propagationBound, max: 4096, clock })
    admission = createEnvelopeAdmission({ acceptedVersions, scope, keyRing, facts,
                                          policyFactory: P11.createPolicyDecision,
                                          securityLog, clock })

per publish or subscribe, after steps 1 to 4:
    result = await admission.admit({ body, contractVersionHeader, agent,
                                     required, requestId })
```

Inside `admit`, in order: steps 5 to 8 (P2; no read) → **one `facts.load`** for the presenter
and the distinct upstream agents (all or nothing) → a request snapshot → origin from the
snapshot (P3) → P11 built over `{ agents: snapshot, humans: U4's source }` → authority (P3) →
stamp, bound, seal (P2) → the result. Every refusal writes one `envelope_refused` event.

## State

| State | Where | Lifetime | Bound |
|---|---|---|---|
| Compiled draft validator | the entry point | the process | one |
| Seal key ring | the entry point | the process; changed by restart | the configured keys |
| Agent-facts cache | the caching decorator | entries up to the propagation bound | 4096 entries per environment |
| In-flight agent reads | the caching decorator | until the batched call settles | the concurrent misses |
| Request snapshot | `admit` | one request | the chain's distinct agents plus one |

Nothing else outlives a call (NFR-AE-22).

## Configuration Items (delivered by U7)

| Item | Where | Secret | Set at |
|---|---|---|---|
| `sealKeys: { current, keys: [{ id, secret }] }` (U2's seed-key shape; each entry names its secret) | `tenancy.yaml`, environment part | No | U7 Infrastructure Design (first key); rotation by the operator |
| Each named seal-key secret | `/run/secrets/`, S4 only | **Yes**: base64url text of 256 random bits, read by `SecretReader.key(secret, true)` | `pnpm stack:init` |
| The propagation bound | configuration (one value) | No | Its value at U6's NFR Requirements |
| Accepted contract versions | P1 (code) | No | U3 Code Generation (`{0.1.0}`) |

## Test Doubles

| Port | Double |
|---|---|
| `AgentFactsSource` | In-memory, with a call counter and an injectable failure |
| Human `GrantSource` | In-memory |
| Clock | Injected; advanced by tests |
| Security log | Collecting |
| Key ring | Fixed test keys, never production files |

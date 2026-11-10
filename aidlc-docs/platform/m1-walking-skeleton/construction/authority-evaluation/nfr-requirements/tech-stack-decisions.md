# Tech Stack Decisions: U3 `authority-evaluation`

**Unit**: U3 `authority-evaluation` (soorma-core#6)
**Scope**: U3's selections. U1's toolchain (T-01 to T-16) and U2's runtime selections (T-OI-01
to 12) apply unchanged
**Dependencies**: **U3 adds none.** Ajv (already in `DEPENDENCIES.md` at 8.20.0, runtime for
`packages/config` and `services/org-gateway`) becomes a runtime dependency of
`packages/envelope` too: its register row gains that workspace at Code Generation

---

## Decisions

| ID | Selection | Choice | Version | Licence | Kind | Why | Source |
|---|---|---|---|---|---|---|---|
| T-AE-01 | Regex engine for Ajv | **V8's default `RegExp`**, gated by U1's pattern check, with the worst-case test (NFR-AE-01, 02) | Node 26.13.0 (U1 T-01) | — | Runtime, built in | Proven linear for the contract's patterns; no native module (`re2` would be the first entry in the empty `allowBuilds`); V8's linear engine is experimental and needs a flag | Q1 A; D-CG-05 |
| T-AE-02 | Schema validation | **Ajv 8**, 2020-12, strict, compiled once at start-up (U1 T-05) | 8.20.0 (in the register) | MIT | Runtime (`packages/envelope`) | Already the contract's validator, at run time in S1 | U1 T-05; P-NFR-01 |
| T-AE-03 | RFC 8785 (JCS) | **In-house**, iterative, over `JSON.stringify` for leaves; lone surrogates refused | — | — | — | About 50 lines; the `canonicalize` package is recursive and accepts lone surrogates, so it would need the same wrapper | Q2 A; Q7 A |
| T-AE-04 | Seal | **HMAC-SHA-256** through `node:crypto` (`createHmac`, `timingSafeEqual`), with a per-environment key ring | Node 26.13.0 | — | Runtime, built in | Only the issuing environment verifies a seal; symmetric is enough, small, and fast. No dependency | Q5 A; Q6 A; U2 T-OI-04 |
| T-AE-05 | Term cache | **In-house** bounded LRU over a `Map`, with TTL from the propagation bound and an injected clock; single-flight on misses | — | — | — | A few dozen lines; `lru-cache` would be a dependency for what a `Map`'s insertion order already gives | Q4 B; NFR-AE-09 to 15 |
| T-AE-06 | Benchmarks | **`vitest bench`** | Vitest 5.0.5 (in the register) | MIT | Development | Ships with Vitest; no new dependency | P-NFR-05 |

## Rejected

| Option | Reason |
|---|---|
| `re2` | A native module with an install script, on every platform, for patterns already proven linear |
| `--enable-experimental-regexp-engine` | Experimental in Node 26; a runtime flag on every deployable |
| `canonicalize` | Recursive (Q7), accepts lone surrogates; no smaller than the in-house version once wrapped |
| Ed25519 seal (`jose` or `node:crypto`) | Public verifiability nobody needs; larger and slower |
| `lru-cache` | A dependency for a few lines |

## Not Decided Here

| Selection | Decided at |
|---|---|
| The seal's form (key identifier, encoding); the key ring's configuration shape | U3 NFR Design |
| The propagation bound's value | The data face's NFR Requirements (U6) |
| Key-ring delivery to S4; the configuration file holding the bound | U7 Infrastructure Design |

## Stages for U3 After This One

| Stage | Decision | Reason |
|---|---|---|
| NFR Design | **Run** | The seal's form and the key ring; the cache as a logical component; the canonicalizer; the entry point's ports |
| Infrastructure Design | **Skip** | U3 has no deployable. The key ring and the bound are delivered to S4 at U7's Infrastructure Design (an obligation on #10) |
| QA construction enrichment | **Run** after NFR Design | qa-test-cases.md §2.6 |
| Construction Design PR gate | **Run** after enrichment | pr-checkpoint.md Section 5 |
| Code Generation | **Run** after the gate | Always |

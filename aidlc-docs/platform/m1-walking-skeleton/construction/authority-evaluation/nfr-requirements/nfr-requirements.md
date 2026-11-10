# NFR Requirements: U3 `authority-evaluation`

**Unit**: U3 `authority-evaluation` (soorma-core#6). Data face, environment level. Modules only
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Decisions from**: the NFR Requirements plan, Q1 to Q7 and P-NFR-01 to 07, answered
2026-11-10 (verbatim in `audit.md`). Every answer is technology (I11); no specification gap
**Companion**: [tech-stack-decisions.md](tech-stack-decisions.md)
**Functional Design**: [../functional-design/business-rules.md](../functional-design/business-rules.md)
(§16 lists what it carried here; every item is answered below)

---

## 1. The Plane-Face Profile: PF §9, carried forward

U3 is a data-face unit citing **PF §9 *NFR Profile*** @ `prd-platform-foundations-v1.3`
(nfr-requirements.md Step 1.5). Its properties are settled. **No control-face property is
added**: no read-your-writes, durability class, or interactive-latency budget.

| Property | PF §9 | Met by |
|---|---|---|
| Latency | The per-request path is the hot path | NFR-AE-06, 07 |
| Availability | High, **bounded by the cache rather than absolute**; caching "decouples per-request authorization from store availability" (M1-NFR-01) | NFR-AE-09 to 15: U3's term reads are cached for the propagation bound, so a store outage within it is invisible |
| Throughput | Scales with total request volume, not with agent count | NFR-AE-06, 22: no cross-request state except the cache; work linear in the draft and the chain |
| Isolation | Per environment; no global list | NFR-AE-09: one cache per environment, built for it; NFR-AE-18: one key ring per environment |
| Revocation propagation bound | One finite, published number | NFR-AE-10: U3's cache TTL **is** that number, not a second one |

## 2. Categories That Do Not Apply

| Category | Status | Reason |
|---|---|---|
| Scalability targets | N/A in M1 | A local stack (M1-NFR-05). U3 is a library in a stateless deployable (M1-TECH-03); its cache is per process and needs no coordination (NFR-AE-09) |
| Availability target | N/A in M1 | No hosted deployment. The availability *class* is met (§1) |
| Durability | N/A | U3 stores nothing |
| Usability | N/A | No user interface; refusals are the contract's |

---

## 3. Requirements

Each has a verification target. Code Generation implements them, and Build and Test runs
them. **Time-based behaviour is tested with an injected clock**, never with real waiting.

### Validation and the Regex Engine (Q1 A; U1 D-CG-05)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AE-01 | Ajv uses **V8's default `RegExp`**. U1's pattern check (D-CG-05: a group under an unbounded quantifier starts, in every alternative, with a literal its body cannot match) stays the **CI gate** for every contract pattern | Q1 A; D-CG-05; SECURITY-05 | U1's pattern check runs in CI |
| NFR-AE-02 | **Worst-case pattern test**: every pattern in the contract is run against a crafted worst-case input at its maximum length, and must complete within a **generous fixed limit of 100 ms**. Catastrophic backtracking takes seconds, so it is caught without timing flakiness | Q1 A, the user's limit | A U3 test over every pattern found in `contract/` |
| NFR-AE-03 | The draft validator (with `inbound.envelope` inside it) is **compiled once, at start-up**, from U1's committed schema. Nothing is compiled per request | P-NFR-01; U1 T-05 | Test: the validator factory runs once per entry-point instance |

### Canonical JSON (Q2 A; Q7 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AE-04 | **RFC 8785 (JCS), in-house**: object keys sorted by UTF-16 code units; numbers and strings serialized as `JSON.stringify` does; **iterative, never recursive**. **A lone surrogate in any string is refused**: for a forwarded envelope it is `invalid_inbound_context` (reason `jcs_invalid`); in a stamped envelope it cannot occur, and would be `internal_error` | Q2 A; RFC 8785 §3.2; Q7 A | RFC 8785's own examples, and a committed set of number and string vectors; a lone-surrogate test |
| NFR-AE-05 | **Each envelope's JCS form is computed once** and used for both the bound and the seal: `inbound.envelope`'s bytes for BR-FX-01 and BR-FX-02; the stamped envelope's bytes for BR-ST-06 and BR-ST-07 | Q2, the user's condition | Test: the canonicalizer is called once per envelope per request (a spy) |

### Latency (Q3 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AE-06 | **Structural bounds, gated in CI**: no storage read before step 9; **at most one read round trip** for all terms on a cache miss (NFR-AE-08); work linear in the draft's size and the chain's length; nothing compiled per request (NFR-AE-03) | Q3 A; PF §9 | Tests with counting ports: zero reads for refusals at steps 5 to 8; one batched call for a 31-agent chain with a cold cache; zero with a warm one |
| NFR-AE-07 | **A number, reported, not gated**: p99 of steps 5 to 10, **excluding term reads**, for a maximum-size forwarding draft with a 31-entry forwarded chain (so a 32-entry stamped chain), target **≤ 2 ms** on the reference workstation, measured with `vitest bench` (P-NFR-05) | Q3 A | Reported at Build and Test, like U2's TC-OI-062 |

### Term Reads and the Cache (Q4 B, as the user specified it)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AE-08 | **One batched read**: one **agent-facts port** returns, for a list of agents in one call, each one's Registration View and standing set together. It is read **once, at the start of step 9**, for the presenter and every distinct upstream agent, **all or nothing**. The Registration View and P11's agent `GrantSource` are served from that read, so the seam stays per principal and P3 is unchanged. *Consistency fix from NFR Design (2026-11-10; the user's agent-facts design)* | Q4 B; NFR Design | Counting-port test (NFR-AE-06) |
| NFR-AE-09 | **An in-process cache** of agent standing sets and Registration Views, as **one caching decorator on the agent-facts port** (P3 and the seam are unchanged). One cache per environment, per process. *Consistency fix from NFR Design (2026-11-10; the user's agent-facts design)* | Q4 B; P-NFR-04; M1-NFR-01; I1 | Test: a second request for the same agents within the TTL makes no read |
| NFR-AE-10 | **Its TTL is the propagation bound**: the one number M1-NFR-01 publishes, read from configuration, **not a second number**. Its value is set at the data face's NFR Requirements (U6). An entry is never served past it | Q4 B; M1-NFR-01; PF §9 | Clock test: served at TTL − 1 ms; re-read at TTL. A configuration test: no separate cache-TTL setting exists |
| NFR-AE-11 | **Bounded in size**: at most **4096 entries** per environment, evicting the least recently used. An evicted entry is simply read again | Q4 B; SECURITY-05 | Test: entry 4097 evicts the least recently used; the count never exceeds 4096 |
| NFR-AE-12 | **Failed lookups are never cached**, and neither is **not found**. A store failure is retried on the next request. A registration created after a not-found is seen at once | Q4 B; D-AE-09, 24 | Tests: a failure, then a success, reads twice; a not-found, then a registration, allows |
| NFR-AE-13 | **Concurrent misses for the same agent are coalesced** into one read. If that read fails, every waiter gets `unavailable`, and nothing is cached | This stage; PF §9 throughput | Concurrency test: 20 parallel requests for one cold agent make one read |
| NFR-AE-14 | **Agent principals only.** A human's grants (`grantedSet` for a human, U4) are never served from this cache: they change in M1 (`grantToHuman`), and a freshly granted human must see the grant | This stage; US-04 | Test: a human principal passes through to `GrantSource` uncached |
| NFR-AE-15 | **A store outage**: entries within their TTL are served; a miss, or an entry past its TTL, is `unavailable` with `Retry-After: 1` (P-NFR-03). The cache never extends an entry's life during an outage | M1-NFR-01; SECURITY-15 | Clock and failure test |
| NFR-AE-16 | **Staleness in M1: none possible.** No M1 operation changes a standing set, a re-broadening declaration, or autonomy declared, or suspends or retires an agent (U5 only creates registrations; PF §7a's other transitions are absent). **The unit that first adds such an operation must account for the cache's staleness window** (up to the propagation bound), by invalidation or by accepting and stating the window | Q4 B, the user's note | A standing note in `aidlc-state.md`; checked at the Units Generation or Functional Design of the unit that adds it |

### The Seal (Q5 A; Q6 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AE-17 | **HMAC-SHA-256** over the JCS bytes, through `node:crypto`. Keys are **at least 256 bits** from a CSPRNG, never logged, never in source or IaC, and never leave their environment (P-NFR-06). **Every seal comparison is constant-time** (`timingSafeEqual`, P-NFR-07) | Q5 A; SECURITY-12, 13; I1 | Test vectors; a test that a seal from another environment's key fails; a review check for `timingSafeEqual` |
| NFR-AE-18 | **A key ring per environment**: the seal names its key; verification accepts any key in the configured ring; sealing uses the one current key. A seal naming a key not in the ring is `invalid_inbound_context` (`seal_failed`). Rotation is a configuration change; **no automatic rotation in M1**. The seal's form (key identifier and encoding) is NFR Design's, within 1024 characters | Q6 A; D-WC-06 | Tests: seal with key 1; rotate to key 2 with key 1 kept: both verify, new seals name key 2; remove key 1: its seals fail |

### Depth (Q7 A)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AE-19 | **No contract depth rule.** JCS, the copy into the stamped envelope, and the size measurement use explicit stacks, never recursion. **The maximum-depth test starts from a fixed raw body string of 1 MiB**, its `inbound.envelope` as deeply nested as it can be within that size. It is parsed (`JSON.parse`, as S4 parses) and run through the entry point. The outcome is deterministic (`invalid_inbound_context` from the seal or the bound), never a crash or a stack overflow. 1 MiB stays valid whatever step-1 limit U7 sets, as long as that limit is at most 1 MiB; U7's own edge test uses its actual limit | Q7 A, the user's conditions (the raw body string; 1 MiB, at NFR Requirements approval) | That test |

### Logging and State (P-NFR-02 to 05)

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-AE-20 | **The security log is a port** with one structured event, `envelope_refused`: code, internal reason, request id, environment, agent, instance (D-AE-26). Never the body, the seal, the forwarded envelope, or trace values. S4 wires it to NestJS's JSON logger (U2 T-OI-11) | P-NFR-02; SECURITY-03 | Test: each refusal emits one event with exactly these fields |
| NFR-AE-21 | `unavailable` from U3 carries `Retry-After: 1` | P-NFR-03; BR-ERR-06 | P1's shared assertion |
| NFR-AE-22 | **No cross-request state** in P2, P3, or P11, other than the cache behind the port (NFR-AE-09) | P-NFR-04; M1-TECH-03 | Review check; two entry-point instances give identical results |
| NFR-AE-23 | Benchmarks use `vitest bench`; no new dependency | P-NFR-05; M1-TECH-04 | `DEPENDENCIES.md` unchanged by U3 except Ajv's runtime row |

---

## 4. Obligations Carried Forward

| To | Item |
|---|---|
| **NFR Design (U3)** | The seal's form: key identifier and encoding, within 1024 characters (NFR-AE-18); the key ring's configuration shape; the cache as a logical component (NFR-AE-09 to 15); the canonicalizer's algorithm (NFR-AE-04); the entry point's ports |
| **Code Generation (U3)** | The contract changes of Functional Design §13 (A6, the step 5 and 6 clarifications, the inbound bound code, pre-release statement 9); Ajv as a runtime dependency of `packages/envelope` (its register row) |
| **Build and Test** | The p99 report (NFR-AE-07); the worst-case pattern test (NFR-AE-02); the maximum-depth test (NFR-AE-19) |
| **U4 (soorma-core#7)** | A human's grants are **not** served from U3's cache (NFR-AE-14). If U4 caches them, it accounts for staleness after `grantToHuman` |
| **U6 (soorma-core#9)** | **The propagation bound is one configured value**, read by P5's revocation cache and by U3's term cache (NFR-AE-10). U6 sets it at its NFR Requirements |
| **U7 (soorma-core#10)** | Wire the cache with the propagation bound; provision each environment's **key ring** (keys ≥ 256 bits; NFR-AE-17, 18) at its Infrastructure Design; S4's JSON parser must survive a maximally nested body, and **U7's edge test uses S4's actual step-1 limit** (U3's own test uses a fixed 1 MiB, so S4's limit must be at most 1 MiB for it to cover S4; NFR-AE-19) |
| **Any unit adding a change to a standing set, declaration, or autonomy, or suspension or retirement** | NFR-AE-16: account for the cache's staleness window. None does in M1 |

---

## 5. Security Compliance at NFR Requirements

| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | N/A at this stage | U3 stores nothing. Key delivery and storage are U7's Infrastructure Design (NFR-AE-17) |
| SECURITY-02, 04, 06, 07 | N/A | No intermediary, web surface, IAM policy, or network configuration in U3 |
| SECURITY-03 | Compliant, **except the centralized log service: not applicable in M1, by the user's decision** (as for U2) | NFR-AE-20 |
| SECURITY-05 | Compliant | NFR-AE-01 to 04, 11, 19 |
| SECURITY-08 | Compliant | Unchanged from Functional Design (deny by default; one place) |
| SECURITY-09 | Compliant | No default key: the ring comes from configuration |
| SECURITY-10 | Compliant | No new dependency (tech-stack-decisions.md) |
| SECURITY-11 | Compliant | Bounded cache; coalesced misses; linear patterns; no recursion on untrusted input |
| SECURITY-12 | Compliant | Key size, source, and handling (NFR-AE-17) |
| SECURITY-13 | Compliant | HMAC seal with constant-time comparison; JCS checked against RFC 8785 vectors |
| SECURITY-14 | **Not applicable in M1, by the user's decision** (as for U2) | The refusal event is named (NFR-AE-20); nothing evaluates it in M1 |
| SECURITY-15 | Compliant | Fail closed past the TTL and on read failures (NFR-AE-12, 15); nothing cached on failure |

**Security findings**: none blocking.

## 6. Invariant Compliance at NFR Requirements

| Code | Status | Note |
|---|---|---|
| I1 | Covered | One cache and one key ring per environment (NFR-AE-09, 18) |
| I2, I3, I4, I6, I9, I10 | No change | As in [invariant-coverage-matrix.md](../functional-design/invariant-coverage-matrix.md) |
| I5 | Covered | The cache serves only values whose staleness cannot occur in M1 (NFR-AE-16), and never human grants (NFR-AE-14); evaluation is unchanged |
| I7 | Covered | No contract change at this stage |
| I8 | Covered | Nothing commercial; no new dependency |
| I11 | N/A | Construction is where technology is selected |

**Invariant findings**: none blocking.

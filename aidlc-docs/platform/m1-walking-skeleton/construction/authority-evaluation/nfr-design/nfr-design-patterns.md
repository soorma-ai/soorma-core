# NFR Design Patterns: U3 `authority-evaluation`

**Unit**: U3 `authority-evaluation` (soorma-core#6). Data face, environment level. Modules only
**Decisions from**: the NFR Design plan, Q1 to Q4 and P-ND-01 to 08, answered 2026-11-10
(verbatim in `audit.md`). P-ND-07 was **replaced by the user's agent-facts design** (NP-04).
All technology (I11); no specification gap
**Meets**: [../nfr-requirements/nfr-requirements.md](../nfr-requirements/nfr-requirements.md)
NFR-AE-01 to 23. **Components**: [logical-components.md](logical-components.md)

**Consistency fixes made at this stage** (the agent-facts design): Functional Design BR-IN-03,
BR-OR-06, BR-AU-03 (wording), BR-AU-09, BR-SEAM-04, §10, §16 (U5), business-logic-model §2
and §3, domain-entities (*Agent Facts*); NFR Requirements NFR-AE-08, 09. Each is marked in
place.

---

## NP-01: The Seal (Q1 A; P-ND-01 to 03)

| Element | Design |
|---|---|
| Form | **`v1.{kid}.{mac}`**, at most 63 characters (within U1's 1024) |
| `kid` | Operator-assigned, `^[A-Za-z0-9][A-Za-z0-9_-]{0,15}$`. No `.` |
| `mac` | `HMAC-SHA-256(key, "soorma.envelope-seal.v1" ‖ 0x00 ‖ JCS bytes)`, base64url without padding: exactly 43 characters (32 bytes) |
| Domain separation | The label and zero byte (P-ND-01): a seal key can produce no MAC valid for any other purpose |
| Sealing | With the ring's **current** key, over the stamped envelope's JCS bytes (computed once, NFR-AE-05) |
| Verification | (1) Parse against `^v1\.([A-Za-z0-9][A-Za-z0-9_-]{0,15})\.([A-Za-z0-9_-]{43})$`; (2) the `kid` must be in the ring; (3) the MAC must decode to 32 bytes and re-encode to the same 43 characters (one encoding per value); (4) recompute over `inbound.envelope`'s JCS bytes; (5) compare with `timingSafeEqual`. **Any failure is `seal_failed`**, and (1) to (3) are decided before any MAC is computed |

Meets NFR-AE-17, 18; BR-FX-02; BR-ST-07. **Verified by**: HMAC test vectors (fixed key,
fixed envelope, literal expected seal); one test per verification failure; a seal under
another environment's key fails; a review check for `timingSafeEqual`.

## NP-02: The Key Ring (Q2 A; P-ND-04, 05)

| Element | Design |
|---|---|
| Configuration | **U2's seed-key shape exactly** (Q2 A; the user's correction at approval): the environment's part of `tenancy.yaml` holds `sealKeys: { current: <kid>, keys: [{ id: <kid>, secret: <secret name> }, …] }`, **naming each key's secret**, never deriving a file name from its id |
| Secret | One secret per key: **base64url text of 256 random bits**, as `pnpm stack:init` writes symmetric keys today, read from `/run/secrets/` (shared-infrastructure.md: one file per secret, never an environment variable). `stack:init` generates the first, and never overwrites one |
| Loading | **Once, at start-up, by P9, through the same path as the seed keys**: `SecretReader.key(secret, true)` (exactly 256 bits). P9 collects every problem and refuses to start. P2's `loadSealKeyRing` then validates what P9 does not: every id matches the `kid` pattern; ids unique; `current` among them. **Any failure stops start-up** (as U2's key ring, BR-CFG-08) |
| Rotation | **Two-phase**, because S4 may run several instances: (1) add the new `{ id, secret }` and its secret to every instance's ring, `current` unchanged, and restart them; (2) once all hold it, make it `current` and restart; (3) after the overlap the operator chooses, remove the old entry and its secret. Making a key current before every instance holds it would make fresh seals fail on the others |
| Isolation | One ring per environment; no file is mounted into another environment's services (I1) |

Meets NFR-AE-17, 18; P-NFR-06. **Verified by**: start-up refusal tests (missing secret, not
base64url, not exactly 256 bits, unknown `current`, duplicate id, bad id); the rotation test (NFR-AE-18). The rotation
procedure is written in `packages/envelope`'s README for U7's operations notes.

## NP-03: The Canonicalizer, `packages/jcs` (NFR Q2 A; NFR Q7 A; Q3 A)

| Element | Design |
|---|---|
| Interface | `canonicalize(value)` → `{ text, bytes }` (the UTF-8 bytes; `bytes.length` is the size the bound measures). Throws `CanonicalizationError` on an input with no RFC 8785 form |
| Algorithm | **Iterative**: an explicit stack of frames (object with its sorted keys and position, or array with its position). No recursion, so depth is bounded only by memory |
| Objects | Keys sorted by UTF-16 code units (`Array.prototype.sort` without a comparator), `key:value` joined by `,` |
| Numbers | ECMAScript `Number.prototype.toString` (what `JSON.stringify` emits), which RFC 8785 adopts; `-0` serializes as `0`. A non-finite number is refused (it cannot come from `JSON.parse`) |
| Strings | **A lone surrogate is refused** (`String.prototype.isWellFormed`); otherwise `JSON.stringify`'s escaping, which RFC 8785 adopts |
| Literals | `true`, `false`, `null` |
| Use in U3 | Called **once per envelope**: `inbound.envelope`'s result serves BR-FX-07, 01, 02; the stamped envelope's serves BR-ST-06, 07 (NFR-AE-05) |

**The swap in U2** (Q3 A, the user's condition), at U3's Code Generation, **in this order**:
1. **Before any change**, commit, against U2's current `canonicalJson`:
   - literal-byte vectors for **the log pseudonym's input** (`referenceJson`), including
     identifiers with every special character the human pattern admits (`'`, `/`, `|`, `@`,
     `+`, `:`, `.`), and the resulting pseudonyms under a fixed test key
   - literal-byte vectors for **the seed associated data** (`{ organization, principal,
     recordId }`)
   - a **fixture seed encrypted by the current code** (key, reference, record id, and the
     stored `{ keyId, nonce, ciphertext, tag }`), and a test that decrypts it
2. Replace `canonical.ts`'s body with a thin wrapper over `@soorma/jcs`, keeping its narrower
   `Canonical` type and its safe-integer check
3. **All of step 1's tests pass unchanged.** Any difference stops Code Generation

Meets NFR-AE-04, 05, 19. **Verified by**: RFC 8785's examples; committed number and string
vectors; a lone-surrogate refusal; a spy test of one call per envelope; the maximum-depth
test (NP-07); the U2 vectors and fixture.

## NP-04: Agent Facts and the Cache (the user's design, replacing P-ND-07)

| Element | Design |
|---|---|
| The port | `AgentFactsSource.load(environment, agents)` → for each agent, `{ registrationView, standingSet }` or **not found**, in **one call**. A failure rejects the whole call. U5 fills it from P4 **with one query** |
| When | **Once, at the start of step 9**, for the presenter and every distinct upstream agent (D-AE-21). Steps 5 to 8 read nothing (NFR-AE-06) |
| All or nothing | A failure is `unavailable` (`agent_facts_read_failed`), and nothing from the call is cached or used. Origin (9a) is then decided before authority (9b), **both from this one read** |
| The snapshot | The read yields an immutable **request snapshot**. 9a reads the presenter's Registration View from it; P11's **agent** `GrantSource` for this request is an adapter over it. So the seam stays per principal, P3 is unchanged, and **no second round trip** is possible. A principal missing from the snapshot is a defect (`internal_error`), never a read |
| Humans | A human principal's `grantedSet` goes **straight to U4's source**, uncached (NFR-AE-14). P11 is built per request over a composite `GrantSource`: agents from the snapshot, humans from U4 |
| The decorator | **One caching decorator on the agent-facts port**: keys `(organization, project, environment, agent)` (P-ND-06); hits within the TTL are served; misses are collected into **one** batched call; an agent already being read by a concurrent request is **awaited, not re-read** (coalescing, NFR-AE-13); only found agents from a **successful** call are stored (NFR-AE-12); if an awaited read fails, this request fails `unavailable` too |
| TTL | The **propagation bound**, from configuration, **measured from when the batched read was issued, not when it completed** (the user's correction at approval): a slow read never extends an entry's life. An entry is never served past it, outage or not (NFR-AE-10, 15). Clock injected |
| Size | At most **4096** entries; least recently used evicted, by deleting and re-inserting on each hit in a `Map` (NFR-AE-11) |

Meets NFR-AE-06, 08 to 15. **Verified by**: counting-port tests (cold 31-agent chain: one
call; warm: none; refusals at steps 5 to 8: none); TTL clock tests, **including one where the
read takes time** (issued at t, completing at t + d: the entry expires at t + TTL, not
t + d + TTL); the eviction test; the
coalescing test; failure tests (nothing cached; awaiting requests also `unavailable`); a
human bypass test; a snapshot test (P11 for an agent never calls the port).

## NP-05: Assembling the Entry Point (Q4 A; P-ND-08)

| Element | Design |
|---|---|
| Framework | **None.** `packages/jcs`, `packages/envelope`, `packages/authority`, `packages/policy-decision`, and `seams/policy-decision` import no NestJS. U7 wraps the entry point in a NestJS provider in S4 |
| Construction | `createEnvelopeAdmission(dependencies)` builds, once: the compiled draft validator (NFR-AE-03), the sealer over the loaded key ring (NP-02), and the cached agent-facts source (NP-04). Dependencies: the accepted versions (P1), the configured scope (P9), the key ring, the agent-facts source, the propagation bound, the policy factory (P11's default, given a `GrantSource`), the security log, and a clock |
| Call | `admit(request)` → `Promise<{ admitted } \| { refused }>`. **An expected refusal is never thrown** (P-ND-08). An unexpected exception propagates to the surface's global error handler, which emits `internal_error` (U2's pattern) |
| Dependencies between packages | P3 depends on P2, `seams/policy-decision`, and `packages/jcs` through P2; **not on P11** (the factory is injected) and **not on P1** (D-AE-25) |

Meets D-AE-04, NFR-AE-03, 22. **Verified by**: a dependency test (no NestJS import in the five
packages; no surface importing P2); construction tests; a test that every refusal is
returned, not thrown.

## NP-06: Validation and the Regex Engine (NFR Q1 A)

The Ajv 2020 instance is created and the draft schema compiled **inside
`createEnvelopeAdmission`**, from the committed contract schema, with V8's default `RegExp`.
**The worst-case pattern test** enumerates every `pattern` in `contract/` (schemas and
OpenAPI documents), builds for each a worst-case input at its maximum length (the pattern's
repeated unit, then a character that fails the match at the end), and asserts each match
completes within **100 ms**.

Meets NFR-AE-01 to 03.

## NP-07: Depth (NFR Q7 A)

JCS (NP-03), the copy of `inbound.envelope` into the stamped envelope, and the size
measurement use explicit stacks. **The copy is in-house and iterative**, not
`structuredClone`, whose depth behaviour is the engine's. **It creates every key as an own
data property** (`Object.defineProperty`, enumerable, writable, configurable), so a key
named `__proto__` is copied as a field and **never sets a prototype** (the user's addition
at approval). A unit test copies an object with a `__proto__` key (as `JSON.parse` produces
it) and checks the copy's prototype is unchanged, the key is an own property, and the JCS
bytes of original and copy are equal. **The maximum-depth test** builds
a **fixed 1 MiB raw body string**, with `inbound.envelope` holding an unknown field nested as
deeply as fits, parses it with `JSON.parse`, and runs `admit`. It expects
`invalid_inbound_context`, never a crash or a `RangeError`.

Meets NFR-AE-19.

## NP-08: The Security Log and Problems

| Element | Design |
|---|---|
| Security log | A port taking one event type, `envelope_refused`, with exactly: code, internal reason, request id, environment, agent, instance (NFR-AE-20). Written once per refusal by `admit` |
| Problems | P1 holds the table and `problemResponse(refusal, requestId)` → `{ status, headers, body }`, framework-neutral (BR-PE-02). S1 keeps a Fastify adapter. **The shared assertion** is P1's test-only export, `@soorma/perimeter/testing` (BR-PE-06) |
| `Retry-After` | `1` on U3's `unavailable` (NFR-AE-21) |

---

## Obligations Carried Forward

| To | Item |
|---|---|
| **Code Generation (U3)** | The U2 swap in NP-03's order, with its stop condition; `sealKeys` in the environment part of the tenancy schema (`packages/config`), loaded through `SecretReader.key(secret, true)` as the seed keys are; the rotation procedure in `packages/envelope`'s README |
| **U5 (soorma-core#8)** | **Fill the agent-facts port with one query**: for a list of agents, each one's Registration View (autonomy declared, re-broadening declaration) and standing set, or not found; a failure fails the whole call. *Replaces the separate Registration View source and agent `GrantSource` posted at Functional Design.* Posted at this stage's approval |
| **U7 (soorma-core#10)** | Generate each environment's first seal key in `pnpm stack:init` as base64url text of 256 random bits, mount its secret only into that environment's S4, and write `sealKeys: { current, keys: [{ id, secret }] }` in the environment's part of `tenancy.yaml`, naming the secret (NP-02); construct the entry point once per S4 instance with the propagation bound and U5's agent-facts source (NP-04, 05); carry the two-phase rotation into the operations notes |
| **U4 (soorma-core#7)** | Supply the human `GrantSource` that P11's per-request composite uses for humans (NP-04). Already implied by the Functional Design obligation; restated with the agent-facts design |

## Security Compliance at NFR Design

| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | N/A at this stage | Key files at rest are U7's Infrastructure Design |
| SECURITY-02, 04, 06, 07 | N/A | No intermediary, web surface, IAM, or network configuration |
| SECURITY-03 | Compliant (centralized log service N/A in M1, the user's decision) | NP-08 |
| SECURITY-05 | Compliant | NP-01 strict seal parsing; NP-06; NP-07 |
| SECURITY-08 | Compliant | Unchanged |
| SECURITY-09 | Compliant | No default key; start-up refuses a missing or malformed ring |
| SECURITY-10 | Compliant | No new dependency; `packages/jcs` is in-house |
| SECURITY-11 | Compliant | Domain separation; coalescing; bounded cache; all-or-nothing reads |
| SECURITY-12 | Compliant | 256-bit keys from files, never environment variables or source |
| SECURITY-13 | Compliant | HMAC with constant-time comparison and one encoding per MAC; the U2 swap guarded by byte vectors and a decryption fixture |
| SECURITY-14 | N/A in M1 (the user's decision) | The refusal event is named |
| SECURITY-15 | Compliant | Fail closed on read failure and past the TTL; start-up stops on a bad ring; refusals returned, defects to the global handler |

**Security findings**: none blocking.

## Invariant Compliance at NFR Design

| Code | Status | Note |
|---|---|---|
| I1 | Covered | Cache keys carry the environment (P-ND-06); one ring per environment, mounted only there (NP-02) |
| I5 | Covered | The snapshot gives origin and authority one consistent read; P3 is unchanged and remains the one place |
| I2, I3, I4, I6, I7, I8, I9, I10 | No change | As in [../functional-design/invariant-coverage-matrix.md](../functional-design/invariant-coverage-matrix.md) |
| I11 | N/A | Construction is where technology is selected |

**Invariant findings**: none blocking.

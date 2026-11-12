# NFR Design Patterns: U6 `agent-credentials`

**Unit**: U6 `agent-credentials` (soorma-core#9). Data face, environment level. S3
`data-gateway`, new
**Decisions from**: the NFR Design plan, Q1 to Q6 and P-01 to P-23, answered 2026-11-12
(verbatim in `audit.md`), with the user's additions: Q1's consistency fixes to NFR-AC-01 and 04
(marked in place) and U7 passing `PROPAGATION_BOUND_MS` to U3's term cache; Q6's check on S2's
image (class 2). Every answer is technology; no specification gap
**Inputs**: [NFR Requirements](../nfr-requirements/nfr-requirements.md) (NFR-AC-01 to 27);
[Functional Design](../functional-design/business-rules.md) (D-AC-01 to 34)
**Companion**: [logical-components.md](logical-components.md)

**The standing rules apply to every change below that touches an earlier unit's code or tests**:
class 1 (items added) and class 2 (strictly stronger) proceed and are recorded; anything else,
including a changed helper an earlier assertion depends on, stops for the user. Each pattern
names its class where it touches U1 to U5.

---

## NP-AC-01: The Three Numbers Are Code (Q1 A; NFR-AC-01, 04, 05)

| Element | Design |
|---|---|
| Where | `packages/credentials/src/lifetimes.ts`, exported from `@soorma/credentials`: `PROPAGATION_BOUND_MS = 60_000`, `AGENT_CREDENTIAL_LIFETIME_MS = 900_000`, `LINEAGE_MAX_AGE_MS = 86_400_000` |
| Why code | PF FR-012: "platform-set and **not tenant-configurable**"; rejected alternative: "a tenant-configurable bound — relocates a safety property into configuration". soorma-core is self-hosted, and the deployer is typically the tenant (PF §6 *Deployment Note*). **No configuration key** for B, L, or M, or for any cache TTL, exists anywhere |
| Who reads them | P5's revocation cache (`PROPAGATION_BOUND_MS`); S3's bootstrap and renewal (L, M); **at U7, S4's cache and U3's term cache**: U7 passes `PROPAGATION_BOUND_MS` as `createCachingAgentFacts`'s `ttl` (the user's instruction) |
| Tests | A unit test: B < L ≤ M (NFR-AC-04). The docs test: `credentials.md`'s *Revocation and Lifetimes* section states 60 s, 15 minutes, and 24 hours, equal to the constants, with L and M as upper bounds and the three client rules (NFR-AC-05). A scan that no configuration schema (`packages/config/schema/`) defines a bound or TTL key |
| Tests that inject | Clock tests build caches and services with the constants or with explicit small values passed as parameters; production wiring always passes the constants |

## NP-AC-02: Two New Migrations (P-01, P-02; the user's rule)

| Migration | Holds |
|---|---|
| `0003_agent_credentials.sql` | U6's tables (NP-AC-03 to 05), each with E's three columns, and their grants (NP-AC-06). Runs after `0002` |
| `0004_attribution_envelope_free.sql` | D-AC-33's check on U4's `attribution_records`, alone, so the amendment to an earlier unit's table is reviewed on its own |

**`0001_init.sql` and `0002_registrations.sql` are not touched.** Both run in `{env}-migrate` as
`soorma_env_migrator`, through `env-store`'s existing runner. **U4's migration test (TC-EHA-068,
`packages/env-store/test/store.test.ts`) pins the applied list**, so it gains the two names,
nothing removed, **class 1**, as U5's D-CG-AR-13:

```diff
-        expect([...x, ...y].sort()).toEqual(['0001_init', '0002_registrations']);
+        expect([...x, ...y].sort()).toEqual([
+          '0001_init',
+          '0002_registrations',
+          '0003_agent_credentials',
+          '0004_attribution_envelope_free',
+        ]);
```

`0004`:

```sql
-- D-AC-33; BR-AT-AC-02: exchangeBootstrap and renewAgentCredential never carry
-- an envelope (GAP-INT-008), so their records carry no chain, and, through
-- attribution_envelope_all_or_none, no origin or re-broadening outcome. The
-- operation itself states why. The writer in packages/attribution refuses the
-- same before any SQL.
ALTER TABLE attribution_records
  ADD CONSTRAINT attribution_envelope_free_operations CHECK (
    operation NOT IN ('exchangeBootstrap', 'renewAgentCredential')
    OR (actor_kind = 'agent' AND chain IS NULL)
  );
```

The constraint validates existing rows: no row uses either operation before U6. The writer half
(P7's closed list) is class 1 for U4's record test (it writes `exchangeBootstrap` with no
envelope, still accepted) and for U5's constructed record (another operation, unaffected).
**The reverse rule stays U7's, under the standing rules.** Tests: the store refuses an
`exchangeBootstrap` record with a chain, and a human-actor `renewAgentCredential` record.

## NP-AC-03: `agent_credentials` (Q2 A; P-03)

```sql
CREATE TABLE agent_credentials (
  id text PRIMARY KEY,                    -- the cid: the lineage (D-AC-14)
  organization text NOT NULL,
  project text NOT NULL,
  environment text NOT NULL,
  agent text NOT NULL,
  instance text NOT NULL,                 -- asserted, never verified (D-AC-23)
  secret text NOT NULL,                   -- the bootstrapping secret record's id
  issued_at timestamptz NOT NULL,         -- the lineage's start
  lineage_ends_at timestamptz NOT NULL,   -- issued_at + M
  expires_at timestamptz NOT NULL,        -- the latest expiry minted
  CONSTRAINT agent_credentials_registration_fkey
    FOREIGN KEY (organization, project, environment, agent)
    REFERENCES registrations (organization, project, environment, agent),
  CONSTRAINT agent_credentials_secret_fkey
    FOREIGN KEY (secret) REFERENCES registration_secrets (id),
  CONSTRAINT agent_credentials_instance_length CHECK (char_length(instance) BETWEEN 1 AND 128),
  CONSTRAINT agent_credentials_expiry_after_issue CHECK (expires_at > issued_at),
  CONSTRAINT agent_credentials_lineage_after_issue CHECK (lineage_ends_at > issued_at),
  CONSTRAINT agent_credentials_expiry_within_lineage CHECK (expires_at <= lineage_ends_at)
);
```

**Times are whole seconds** (truncated before writing), so a token's `exp` and the record agree
exactly. Statements (in `packages/credentials/src/sql.ts`, through service-kit's `statement()`,
every one constrained on the three environment columns):

| Statement | Form |
|---|---|
| Insert | One row, new `cid` (128 random bits) |
| Read by `cid` | `agent`, `instance`, `lineage_ends_at`, `expires_at`, by `id` and E |
| Renew | `UPDATE agent_credentials SET expires_at = GREATEST(expires_at, $new) WHERE id = $1 AND <E> AND agent = $a AND instance = $i RETURNING lineage_ends_at`: the binding is in the `WHERE`, so a mismatched token updates nothing (`record_mismatch`) |

`$new` = min(now + L, `lineage_ends_at`), computed by S3 from the row it read in the same
transaction. U4's `credentials` table, constraints, and grants are untouched.

## NP-AC-04: Revocation State, Two Tables (Q5 A; P-04)

```sql
CREATE TABLE credential_revocations (
  organization text NOT NULL,
  project text NOT NULL,
  environment text NOT NULL,
  credential text NOT NULL,
  revoked_at timestamptz NOT NULL,
  CONSTRAINT credential_revocations_pkey PRIMARY KEY (organization, project, environment, credential),
  CONSTRAINT credential_revocations_credential_fkey
    FOREIGN KEY (credential) REFERENCES agent_credentials (id)
);

CREATE TABLE agent_revocations (
  organization text NOT NULL,
  project text NOT NULL,
  environment text NOT NULL,
  agent text NOT NULL,
  revoked_at timestamptz NOT NULL,
  CONSTRAINT agent_revocations_pkey PRIMARY KEY (organization, project, environment, agent),
  CONSTRAINT agent_revocations_registration_fkey
    FOREIGN KEY (organization, project, environment, agent)
    REFERENCES registrations (organization, project, environment, agent)
);
```

**The direct source** (D-AC-01), one statement, its answer `revoked` or `not_revoked`:

```sql
SELECT EXISTS (SELECT 1 FROM credential_revocations
                WHERE organization = $1 AND project = $2 AND environment = $3 AND credential = $4)
    OR EXISTS (SELECT 1 FROM agent_revocations
                WHERE organization = $1 AND project = $2 AND environment = $3 AND agent = $5)
    AS revoked
```

At bootstrap only the agent half applies (no `cid` yet: `$4` is null, which matches nothing).
Each target must exist in E (the foreign keys), so a seeded revocation can never name another
environment's credential or agent (I1). **Terminal**: nothing but the owner can update or delete
(NP-AC-06).

## NP-AC-05: The Cache, Per Credential, Read Through (Q3 A; P-17)

`packages/credentials/src/revocation.ts`: `createRevocationCache(source, { ttl, max = 16384,
clock })`, modelled on U3's `createCachingAgentFacts` (NP-04):

| Rule | Design |
|---|---|
| Key | (organization, project, environment, `cid`, agent), joined unambiguously (I1) |
| Entry | The answer and the time its read was **issued** |
| Hit | `not_revoked` younger than `ttl`: served. `revoked`: served while held (terminal) |
| Miss or stale | One read through the direct source. **Concurrent misses for one key share one read** (an in-flight map) |
| Failure | Never cached. A stale-but-younger-than-`ttl` entry is still served (it is, by definition, not stale); with none, the answer is **unknown → deny** (`unavailable`) |
| Bound | At most 16,384 entries, oldest inserted first evicted. An evicted entry is re-read: a `revoked` target re-reads as `revoked`, so eviction never admits (NFR-AC-15) |
| `ttl` | `PROPAGATION_BOUND_MS` in production (NP-AC-01) |
| Used by | **S4, wired at U7.** S3 uses the direct source inside its transaction (D-AC-01) |
| Tests | NFR-AC-01's timeline (business-logic-model §5) with an injected clock; failures never cached; shared in-flight reads; eviction at the bound; `pnpm bench:revocation` (NFR-AC-16) |

## NP-AC-06: Privileges, Their Test, and Test-Only Seeding (P-07 to P-09)

`0003` ends:

```sql
REVOKE ALL ON agent_credentials, credential_revocations, agent_revocations,
  attempt_slots, failed_bootstrap_attempts FROM PUBLIC;
GRANT SELECT, INSERT ON agent_credentials TO soorma_env_app;
GRANT UPDATE (expires_at) ON agent_credentials TO soorma_env_app;
GRANT SELECT ON credential_revocations, agent_revocations TO soorma_env_app;
GRANT SELECT, INSERT, UPDATE ON attempt_slots TO soorma_env_app;
GRANT INSERT ON failed_bootstrap_attempts TO soorma_env_app;
GRANT USAGE ON SEQUENCE failed_bootstrap_attempts_id_seq TO soorma_env_app;
```

**No `DELETE` anywhere.** The privilege test is a **new** test beside U4's TC-EHA-080 in
`packages/env-store/test/`, in its pattern (each forbidden statement, run as the app role, fails
with permission denied); U4's cases are unchanged. Forbidden: `INSERT`, `UPDATE`, or `DELETE` on
either revocation table; `UPDATE` of any `agent_credentials` column but `expires_at`; `UPDATE` or
`DELETE` on `failed_bootstrap_attempts`; `DELETE` on `agent_credentials` or `attempt_slots`.

**Seeding** (M1-FR-07): the store's test harness gains a fixture that inserts revocations as the
owner. On the running stack, `e2e/support` gains a helper running `psql` inside `{env}-db`
through `docker compose exec`, as `soorma_env_migrator`, reading the migrator's password from its
mounted secret file. Neither is in any package's `src/` or any image (NP-AC-10 checks the image).

## NP-AC-07: The Bound in the Environment Store, and P8's Generic Core (Q4 A; P-05, 06, 12, 13)

**Tables** (in `0003`):

```sql
-- U2's org-store table, the same name and columns, so P8's statements run in
-- either store (one per environment here, I1).
CREATE TABLE attempt_slots (
  slot integer PRIMARY KEY CHECK (slot BETWEEN 0 AND 1048575),
  entries jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(entries) = 'array'),
  consecutive integer NOT NULL DEFAULT 0 CHECK (consecutive >= 0),
  next_allowed_at timestamptz
);

CREATE TABLE failed_bootstrap_attempts (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  organization text NOT NULL,
  project text NOT NULL,
  environment text NOT NULL,
  agent text NOT NULL,
  at timestamptz NOT NULL,
  refused_by_bound boolean NOT NULL,
  reason text NOT NULL CHECK (reason IN ('bound_refused', 'unsupported_material',
    'malformed_secret', 'unknown_secret', 'secret_not_active', 'secret_mismatch',
    'registration_not_registered', 'agent_revoked', 'store_unavailable')),
  CONSTRAINT failed_bootstrap_attempts_registration_fkey
    FOREIGN KEY (organization, project, environment, agent)
    REFERENCES registrations (organization, project, environment, agent)
);
```

The batch insert **joins `registrations`**, so an attempt on an agent that does not exist in E
writes nothing, decided by the statement, off the response path (BR-FA-02):

```sql
INSERT INTO failed_bootstrap_attempts
  (organization, project, environment, agent, at, refused_by_bound, reason)
SELECT u.organization, u.project, u.environment, u.agent, u.at, u.refused_by_bound, u.reason
  FROM unnest($1::text[], $2::text[], $3::text[], $4::text[], $5::timestamptz[],
              $6::boolean[], $7::text[])
       AS u(organization, project, environment, agent, at, refused_by_bound, reason)
  JOIN registrations r
    ON r.organization = u.organization AND r.project = u.project
   AND r.environment = u.environment AND r.agent = u.agent
```

**P8's generic core** (`packages/abuse-bound`):

| Part | Design |
|---|---|
| `slotOfKey(canonical, counterSecret)` | HMAC-SHA-256 of a canonical string, the last 4 bytes big-endian, mod 2^20: U2's arithmetic, extracted |
| `SlotBound` | `new SlotBound(store, counterSecret, clock, limits)`; `admit(canonical)`, `settleFailure`, `settleSuccess`; `limits = { windowMs, maxLive, backoffFrom, backoffCapSeconds }`, passed to the existing statements, which already take them as parameters |
| `BatchWriter<T>` | U2's queue, batching, interval, drop counting, and shutdown flush, with the insert statement and the row-to-parameters mapping as constructor arguments |
| **U2's API, kept** | `slotOf(reference, counterSecret)` = `slotOfKey(referenceJson(reference), counterSecret)`; `AbuseBound(store, counterSecret, clock)` = a `SlotBound` with U2's constants as limits, `admit(reference)` passing `referenceJson(reference)`; `FailedAttemptWriter` = a `BatchWriter` with U2's statement and mapping; every exported constant unchanged. **U2's tests and canonical vectors run unchanged**; if one would change, Code Generation stops (class 3) |
| The agent's slot key (P-12) | `agentSlotKey(environment, agent)` = the RFC 8785 form of `{ "agent": …, "environment": { "environment": …, "organization": …, "project": … } }` (through `@soorma/jcs`, a workspace package already locked); new canonical vectors in P8's tests |
| The agent's limits | `{ windowMs: 60_000, maxLive: 60, backoffFrom: 10, backoffCapSeconds: 60 }` (NFR-AC-06, 07), exported as `AGENT_BOOTSTRAP_LIMITS`. A security bound, not a tenant quota (NFR-AC-27) |
| The manifest (D-AC-12) | `@soorma/org-identity` moves to `devDependencies`; P8 gains `@soorma/jcs` as a dependency |

## NP-AC-08: The Seam's Agent Half and `packages/agent-identity` (P-10, P-11)

**Seam types** (`seams/identity-resolution/src/agent.ts`, Apache 2.0, re-exported beside the
human half, which is unchanged):

```ts
export type AgentMaterialType = 'registrationSecret';
export interface AgentRegistrationReference {
  environment: { organization: string; project: string; environment: string };
  agent: string;
}
export type AgentResolution =
  | { resolved: true; registration: AgentRegistrationReference; secretId: string }
  | { resolved: false };
export interface AgentIdentityResolver {
  resolve(type: AgentMaterialType, claimed: AgentRegistrationReference, material: string): Promise<AgentResolution>;
}
```

**`packages/agent-identity`** (FSL): `createAgentIdentityResolver({ store, onRejected })`.
Dependencies: `@soorma/identity-resolution-seam`, `@soorma/registry`, `@soorma/env-store`,
`@soorma/service-kit`; nothing else.

| Step | Design |
|---|---|
| 1 | Prefix `soorma_rs_`, else reject (`unsupported_material`) |
| 2 | `parseRegistrationSecret`, else reject (`malformed_secret`); the digest of the parsed bytes computed now, before the read (D-AC-34) |
| 3 | **One statement**, constrained on the three environment columns: the secret row by `id` (its `registration`, `state`, `digest`), and whether the claimed agent exists (for the log reason only) |
| 4 | No row, or `registration` ≠ the claimed agent: reject (`unknown_secret`; `unknown_registration` when the agent does not exist). Not `active`: reject (`secret_not_active`). `registrationSecretMatches` false: reject (`secret_mismatch`) |
| 5 | Else `{ resolved: true, registration, secretId }` |
| Rejections | Always `{ resolved: false }` through the seam type; the reason goes **only** to `onRejected(reason)`, which S3 wires to its security log and the failed-attempt writer |
| A store failure | Thrown as service-kit's `UnavailableError`; S3 answers `unavailable` and settles the bound as a failure |

## NP-AC-09: The Agent Key Ring and Token (P-14 to P-16)

| Element | Design |
|---|---|
| Loader | **U4's `loadEnvironmentKeyRing({ verify, signing })`, unchanged**, over the agent ring's own secrets, named in S3's configuration part only. S2's part never names them; S3's never names the human ring (the Compose-model test, Infrastructure Design) |
| Rotation | U4's three steps (add a verify key; make it the signing key; remove the old one), with the old key's verify half kept **at least 15 minutes** (L) after it stops signing (NFR-AC-19); S3's README *Operations* |
| Token module | `packages/credentials/src/agent-token.ts`: `mintAgentCredential(claims, ring)`, `verifyAgentCredential(token, ring, environment, now)`: NP-EHA-01's steps 1 to 8 for prefix `soorma_ac_`, `typ` `soorma-ac+jwt`, claims `env`, `sub`, `inst`, `cid`, `jti`, `iat`, `exp`. **U4's `token.ts` is not refactored**; the shared steps are duplicated in this one file |
| Kind tests | A `soorma_ec_` token's JWS behind `soorma_ac_` is refused by `verifyAgentCredential` (its `typ`, and an unknown `kid` against the agent ring); a `soorma_ac_` token's JWS behind `soorma_ec_` is refused by U4's `verifyEnvironmentCredential` (a new test of U4's function, its own tests unchanged: class 1) |
| S4 | Verify halves only, from U7's loader variant (U7's obligation) |

## NP-AC-10: Closure, in the Manifests and in the Images (Q6 A, with the user's addition; P-18, 19)

| Check | Design | Class |
|---|---|---|
| **S3's manifest walk** | `services/data-gateway/test/closure.test.ts`, on S2's walk: `@soorma/data-gateway`'s production closure contains `@soorma/service-kit`, `@soorma/credentials`, `@soorma/agent-identity`, `@soorma/abuse-bound`, and **never `@soorma/org-identity` or `@soorma/identity-resolution`**; S3's sources import nothing from `@soorma/authority`. P8's manifest move (D-AC-12) lands in the same commit, so the test proves it | New (U6) |
| **S3's image** | A new check, `node tools/checks/run.ts image-packages --image <ref> --forbid <name>[,<name>]`: it exports the image's file system as the secrets check does, and fails on any path containing `@soorma/<forbidden>` or any `package.json` whose `name` is a forbidden package. In CI's image job, after S3's secret scan: forbid `@soorma/org-identity` and `@soorma/identity-resolution` | New (U6) |
| **S2's image** (the user's addition) | The same check on `soorma/control-gateway:local`, **forbid `@soorma/org-identity`**, in the image job beside S3's, after S2's secret scan. **S2's manifest test (TC-EHA-078) stays unchanged** | **Class 2**: strictly stronger, S2's existing checks unchanged; recorded |
| A positive control | The check run on S1's image **finds** `@soorma/org-identity`, so it is not vacuous (as TC-EHA-078's second case does for the walk) | New |

## NP-AC-11: S3's Composition and Transactions (P-20 to P-22)

| Element | Design |
|---|---|
| App | `services/data-gateway`, NestJS on service-kit's Fastify adapter, exception filter, contract validator (compiled once from `contract/data-gateway.openapi.yaml`), security log, and health listener, as S2. The throttle installed before step 1 (NFR-AC-12) |
| Bootstrap | Body checks (steps 1, 2, 5, 6); P8 `admit(agentSlotKey(E, agent))`; P6's agent half (outside any transaction: one read); then **one transaction** (`env-store`'s `withTransaction`): the registration's `state` and `sponsor`; the direct revocation source (agent half); the record insert; the attribution record. Then settle; then mint. A rejection or failure queues a Failed Bootstrap Attempt |
| Renewal | Presenter; then **one transaction**: `checkAgentRequest` with a revocation callback bound to the transaction (O1, O2, O4 before any read; then O3 at both granularities); the record by `cid`; the registration's `state` and `sponsor`; the renew statement; the attribution record. Then mint |
| `checkAgentRequest` (P1) | Takes `verify(token)` and `revocation(context)` callbacks (as U4's `SignInPerimeter` takes its key source and status), so `@soorma/perimeter` gains no dependency on P5 |
| Responses | `200`, `Cache-Control: no-store`, the token a `SecretText` until serialised |

## NP-AC-12: The Secret-Pattern Check Learns U6's Values (made at design; flagged for review)

U2's secret-pattern check (`tools/checks/secrets.ts`) knows enrollment material, sign-in tokens,
and private keys. U6 adds two patterns, **shaped like the real values** so placeholders in tests do
not match: **an agent credential** (`soorma_ac_` followed by a JWS's three base64url parts, as the
sign-in pattern) and **a registration secret** (`soorma_rs_` + 22 + `.` + 43 base64url
characters). It runs over the repository and every image, as now. **Class 2**: it scans for more,
the existing patterns unchanged; recorded with its diff at Code Generation. Labelled fixtures
stay listed in `FIXTURE_PATHS`.

*Approved with the user's condition (2026-11-12)*: **if a test fixture would trip the new
patterns, it uses obviously fake values** (shaped so they do not match, as U2's `soorma_em_x`),
**never an exception in the check**: no new entry in `FIXTURE_PATHS`, no allowlist, no skip.

## NP-AC-13: Identifiers and Time

Every id (`cid`, `jti`) from Node's CSPRNG, 128 bits, base64url (`env-store`'s `newRecordId`).
Time from the injected `Clock`, truncated to whole seconds for tokens and records; never the
database's `now()` (as U2's P-14).

---

## Security Compliance at NFR Design

| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | Compliant in transit; **at rest not applicable in M1, by the user's decision** | No token or secret value in the store (NP-AC-03: the secret's id only) |
| SECURITY-02, 07 | N/A at this stage | S3's network and ports are Infrastructure Design's |
| SECURITY-03 | Compliant, **except the centralized log service, by the user's decision** | Rejection reasons reach only the security log and the failed-attempt record (NP-AC-08); never a secret, id, digest, or token; NP-AC-12 scans for them |
| SECURITY-04 | N/A | No HTML |
| SECURITY-05 | Compliant | Constant SQL with bound values (NP-AC-03, 04, 07); closed schemas |
| SECURITY-06 | Compliant | Separate key rings (NP-AC-09); the narrowest grants (NP-AC-06); revocation `SELECT` only |
| SECURITY-08 | Compliant | Renewal verified per request; the binding in the renew statement's `WHERE` (NP-AC-03) |
| SECURITY-09 | Compliant | B, L, M not configurable (NP-AC-01); generic Problems |
| SECURITY-10 | Compliant | No new external dependency; P8 gains `@soorma/jcs` (workspace); closure checked in images (NP-AC-10) |
| SECURITY-11 | Compliant | The bound in the store, atomic per slot (NP-AC-07); the throttle |
| SECURITY-12 | Compliant | Constant-time compare (NP-AC-08); no hard-coded credential; NP-AC-12 |
| SECURITY-13 | Compliant | Attribution in the same transaction; `0004`'s check; terminal revocations |
| SECURITY-14 | **Not applicable in M1, by the user's decision** | Events and alert rules as files |
| SECURITY-15 | Compliant | Fail closed: store failures `unavailable`; cache failures never cached and deny past B |

**Security findings**: none blocking.

## Invariant Compliance at NFR Design

| Code | Status | Note |
|---|---|---|
| I1 | Covered | Every new table has E's three columns; foreign keys keep revocations and failed attempts within E (NP-AC-04, 07); the cache key includes E (NP-AC-05) |
| I2 | Covered | No change: every check at S3 from the raw request |
| I3 | Covered | Identity only from the verified secret (NP-AC-08) or token (NP-AC-09) |
| I4 | Covered | `0004`'s check makes BR-AT-AC-02 structural in the store |
| I5 | Covered | S3 imports nothing from `@soorma/authority` (NP-AC-10) |
| I6 | Covered | S3 its own deployable and contract document |
| I7 | Covered | B, L, M published from the same constants (NP-AC-01) |
| I8 | Covered | The agent limits a security bound (NP-AC-07); seeding outside every image (NP-AC-06, 10) |
| I9, I10 | Covered | No tenant constant; the instance asserted and stored as given |
| I11 | N/A | Construction is where technology is selected |

**Invariant findings**: none blocking.

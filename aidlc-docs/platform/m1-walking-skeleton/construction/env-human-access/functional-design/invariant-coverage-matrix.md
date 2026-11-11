# Invariant Coverage Matrix: U4 `env-human-access`

**Invariants source**: soorma-prd `references/platform/invariants.md` @ `prd-identity-v1.0`
and @ `prd-platform-foundations-v1.3`. The text is identical at both tags (re-checked
2026-11-11, at this unit's resumption).
**PRD compliance tables**: ID §15 @ `prd-identity-v1.0` (the main one for this unit) and PF §15
@ `prd-platform-foundations-v1.3`: **I1 to I11 Addressed in both, none N/A, none Gap**.

**Status values**: `Covered` · `N/A` (with a reason) · `Missing` (blocking). Code Generation
moves rows to `Implemented`; Build and Test to `Verified`. *QA enrichment* marks a test case the
QA construction enrichment adds before the Construction Design PR gate.

**Result**: I1 to I10 `Covered`; I11 `N/A`. **0 `Missing`.** I1, I3, I4, I5, and I6 are this
unit's centre.

| Code | PRD Status | Applies to Unit | Code-Level Risk in This Unit | Implementation Target | Verification Target | Status |
|---|---|---|---|---|---|---|
| I1 Isolation | Addressed | **Yes** | A query over grants, credentials, or attribution records with no environment constraint; a credential accepted in another environment; minting or sign-in material shared across environments; a human named in logs by a key shared across environments | **Access paths** (all in E's own store, D-EHA-29: every row carries the environment and every read and write constrains on it): the credential record (issue, O3, renew, end); the Grant (write; the held-set read behind P11); the configuration grant (start-up); the attribution record (write). **Material**: E's own minting material only (BR-EC-02, 03); verify-only keys for sign-ins (BR-IS-05). **Calls**: S2 joins only `org-internal-{E}` and signs as E (BR-OL-02, 03). **Logs**: E's own log-pseudonym key (D-EHA-18) | TC-EHA-010; TC-EHA-022; *QA enrichment*: one test per access path showing a principal of E cannot read, write, or present anything of E2's | Covered |
| I2 Perimeter enforcement | Addressed | Yes | A check relying on the client (there is no human client library, ID §11); S2 trusting a sign-in because S1 issued it; an operation reachable without its checks | Every operation runs its full check order at S2 from the raw request (§11); the sign-in is verified at S2 (BR-IS-01, 03; O10); the presenter matrix is enforced by kind (BR-PR) | TC-EHA-009; TC-EHA-015; TC-EHA-016; TC-EHA-024 (raw calls); *QA enrichment*: a forged sign-in and a forged environment credential, sent raw | Covered |
| I3 Portable credential | Addressed | **Yes** | Identity or environment taken from the network (the internal network, a source address); S1 trusted for its location; the first Admin inferred from the deployment | Identity only from the presented, verified credential (Checked Human Context; BR-EC-10); environment from configuration, compared with the credential's (D-EHA-12); internal calls signed whatever the network (BR-OL-02, 03), S1 authenticated by certificate (D-EHA-27); the first Admin from configuration (BR-FG-04) | TC-EHA-010; *QA enrichment*: the same credential from another source address resolves the same; a request with no credential on the internal network is refused | Covered |
| I4 Attribution recoverable | Addressed | **Yes** | A grant or credential operation with no record; scope, actor, and origin collapsed; an agent record missing its sponsor, chain, or re-broadening outcome (U6, U7 write them through U4's writer); a record written apart from its operation | D-EHA-03, 04, 17, 31; BR-AT-01 to 09. **Governed record types** and where scope, actor, chain, origin are written: the Attribution Record (all four; chain and origin absent by rule for human and configuration actors, BR-AT-02, 03); the Grant (`grantedBy`, scope); the credential record (subject, `issuedFrom`) | TC-EHA-005; TC-EHA-021; *QA enrichment*: reconstruction from the record alone for each actor kind, at zero hops and across a multi-hop chain (business-logic-model §7) | Covered |
| I5 Monotonic authority | Addressed | **Yes** | A second place computing a human's authority (S2, P4, or P7 testing a set); a human-only permission reaching an agent through U4; renewal widening authority; authority taken from the credential | D-EHA-13; BR-EV-01 to 06 (one place, P3); D-EHA-10 (the credential carries no authority); BR-PR-04 (no agent reaches S2); P3's human-only refusal for agents unchanged (U3 BR-AU-03). Origin and chain across hops: not applicable to a direct human operation (no envelope); U3 and U7 hold them | TC-EHA-012; TC-EHA-015; *QA enrichment*: S2 imports no evaluator but P3's; renewal adds no authority | Covered |
| I6 Two faces | Addressed | **Yes** | A data-face operation added to S2, or S2's operations added to a data-face document or deployable; one NFR configuration for both faces | S2 is a control-face deployable, separate from S3 and S4; `contract/control-gateway.openapi.yaml` holds control operations only (§13); one NFR profile, ID §10 (unit-of-work.md) | Contract check: `control-gateway.openapi.yaml` holds no data-face operation; S2 serves no `soorma_ac_` | Covered |
| I7 Contract compatibility | Addressed | Yes | A new operation or code unclassified; a change to a published shape | Every change classified (§13, `contract/CHANGELOG.md`); new codes in an open set; new operations only; U2 amendment A7 is internal, unpublished | U1's compatibility check over the changed contract; TC-EHA-024 | Covered |
| I8 Packaging rule | Addressed | Yes | A commercial capability (separation of duties, grant mappings populated by sources, an org role model, an audit product) built into core, enabled or stubbed; a core API narrowed | Packaging table below | Packaging table, re-checked at Code Generation and at Build and Test | Covered |
| I9 Mechanism, not instance | Addressed | Yes | A tenant's identifiers, roles, or principals hard-coded | Only plane-declared identifiers appear in code (BR-ACC-01); principals come from configuration and requests; no role names | Code Generation review | Covered |
| I10 Runtime-later | Addressed | Yes | Enforcement assuming a managed runtime; scope keyed on deployment topology | Tenancy from configuration (P9); nothing at S2 reads a host, cluster, or deployment label (BR-EC-10); nothing depends on code identity | Code Generation review | Covered |
| I11 No technology selection | Addressed | N/A | — | — | — | N/A: Construction is where technology is selected |

## I8 Packaging Table

ID §12 assigns 49 items to core and 7 to commercial; PF §12, 52 and 8. Every U4 capability is
a core item, and lands in `soorma-core`.

| Capability U4 implements | Assignment | Repository |
|---|---|---|
| The Human Environment Credential (record, issuance by E, renewal, end) | ID §12 core: records; operations (§8a) | soorma-core |
| The human credential contract at the Gateway; refusal beside an agent's credential | ID §12 core: contracts; obligations | soorma-core |
| The first grant by configuration, and recovery by configuration | ID §12 core: mechanisms (first grant and recovery) | soorma-core |
| The `grant:human` ceiling, self-grants recorded | ID §12 core: mechanisms (the ceiling) | soorma-core |
| `human:manage`, `agent:delegate` human-only (their declaration in the accepted set) | ID §12 core: contracts | soorma-core |
| Grant to a human principal (PF's operation) | PF §12 core: operations | soorma-core |
| The minimal permission model's grants and evaluation for humans (`evaluateHuman`) | PF §12 core: mechanism; seam default | soorma-core |
| Attribution recording | PF §12 core (record); ID FR-018's commercial audit product not built | soorma-core |
| Fail closed without fresh state; non-disclosing denial | ID §12 core: obligations | soorma-core |

**Not built, and absent from core in any form**: separation of duties (prohibiting self-grant;
constraining who grants domain permissions), grant mappings populated by configured sources,
the org role model, IdP configuration and federation, lifecycle audit, and cross-environment
identity views (ID §12 commercial). No flag, stub, or disabled path for any.

## Invariant Findings

None. GAP-EHA-001 bears on I1 and on the organization level's place (ID FR-009); it is resolved
by keeping the organization level off the per-request path (D-EHA-01).

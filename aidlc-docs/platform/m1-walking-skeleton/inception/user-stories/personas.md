# Personas: soorma-core M1 Walking Skeleton

**Sources**: PF §3 @ `prd-platform-foundations-v1.3` and ID §3 @ `prd-identity-v1.0`.
**The principals are carried verbatim and never re-derived.** Where the two PRDs describe
the same principal, both are cited. Grants are those the PRDs assign. *In M1* states which
of them this repository builds (see [requirements.md](../requirements/requirements.md)).

**Roles are not records** (ID §3, OQ-2). *Admin* means a holder of `grant:human` and
`human:manage`. The names describe who typically holds what. **Roles compose; they do not
nest.**

---

## Principals

| Persona | Type | Scope | Grants held (per the PRDs) | Face; entry points | In M1 |
|---|---|---|---|---|---|
| **First Admin of an environment** | Human | One environment, from configuration (ID §3) | `grant:human`, `human:manage`, granted by configuration (ID FR-004) | None until first sign-in; then control, at the Gateway | **Yes.** The one human in M1. Configured by the deployer; activates; self-grants Developer permissions (ID §1 trace, steps 2 to 5) |
| **Admin** | Human | Organization identity; per-environment grants (PF §3, ID §3) | `grant:human`, `human:manage` where held. PF §3: manages all credentials; initiates revocation for any principal; grants to humans; reads attribution environment-wide | Control; Gateway | **In part.** Granting to humans (M1-FR-15) is built. Revocation initiation (PF FR-011), others' credentials (ID FR-012), lifecycle (ID FR-003), and the attribution read (PF FR-025 read) are absent |
| **Developer** | Human | Organization identity; per-environment grants (PF §3, ID §3) | PF's agent permissions: registers logical agents; sponsors standing authority; issues, rotates and retires secrets for agents they sponsor; initiates revocation for them (BD-1); reads their attribution. `agent:delegate` (ID §3) | Control; data only through a delegated chain (ID §3); Gateway | **In part.** Registration and sponsorship (M1-FR-03) and secret issuance (M1-FR-04) are built. Rotation, retirement, revocation initiation, the attribution read, and delegation are absent |
| **Agent**, logical | Agent | Environment | Its standing set, capped by the sponsor ceiling snapshot; **never a human-only permission** (PF §3, ID §3) | Data; Gateway and Event ingest | **Yes.** Two of them, A and B, each **registered with autonomy declared** (A-5) |
| **Agent**, instance | Agent | Environment | Inherits the logical agent's (PF §3) | Data | **Yes.** Bootstraps, renews, publishes, subscribes. The instance identifier is asserted, not verified |
| **Operator**, **SME** | Human | Organization | **None** (PF §3: none in this initiative; ID §3: none from this PRD) | Control (self-service) (ID §3) | **No story.** They exist as humans, but M1 configures only the first Admin and registers no further humans (ID FR-002 out) |
| **Configured identity source** | **Not a principal** (ID §3, BD-2) | Organization; environments configured over | None; exactly its configuration | Control; Gateway | **Absent** (ID FR-024 out) |

**Origin modes**: humans have none (ID §3). An agent is delegated, or autonomous if it
declared autonomy (PF §3). **In M1 every chain starts autonomous**, because delegation is
absent (A-5).

**Agent developers** write the code behind the Agent persona. In M1 they make **raw calls
to the wire contract without the SDK**. That is how this repository proves *done when* 2
and 3 (PF FR-023). They are not a separate actor (story plan Q1 B).

---

## Non-Principal Actor

| Actor | Type | What they do in M1 | Grants | Why they are a persona |
|---|---|---|---|---|
| **Deployer** | **Not a principal** | Writes the deployment's configuration: the organization, project, and environment identities and membership, and each environment's first Admin with single-use enrollment material (ID FR-004, FR-007; M1-FR-14) | **None.** Never holds a working credential (ID FR-007) | **The deployment's configuration is the trust root** (ID FR-004). *Done when* 1 starts here (ID §1 trace, steps 1 and 2) |

---

## The M1 Single-Actor Form

**One human, H, is both the first Admin and the Developer.** This rests on three sources:
- ID §12 *Core Single-Actor Form*: "One person, one organization, one environment:
  configured as first Admin; sets K (and P if they choose); self-grants Developer
  permissions; registers and sponsors agents; delegates to an agent to test it; offboards
  and recovers through configuration"
- ID §3: roles compose, they do not nest. An Admin may self-grant any permission valid in
  the environment, and each self-grant is an auditable grant
- ID §1 trace, step 5: H self-grants `agent:register`, `event:publish`, and
  `event:subscribe` in E

**M1 builds the first four steps of ID §12's form**:
1. configured as first Admin (M1-FR-14)
2. sets K, and P (M1-FR-17)
3. self-grants Developer permissions (M1-FR-15)
4. registers and sponsors agents (M1-FR-03)

**Absent**:
- delegating to an agent (ID FR-019 to FR-021)
- offboarding and recovery (ID FR-003, FR-012; see *Absent from M1* in requirements.md)

A lost K or P is unrecoverable in M1.

**Separation of duties: none in core** (PF §3, ID §3). That H registers, sponsors, and
self-grants is the specified single-actor form, not an M1 shortcut.

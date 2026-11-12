# Deployment Architecture: U6 `agent-credentials`

**Unit**: U6 `agent-credentials` (soorma-core#9)
**Companion**: [infrastructure-design.md](infrastructure-design.md) (D-ID-AC-01 to 18)

---

## The Local Stack After U6

```text
+----------------------------------------------------------------+
| host loopback 127.0.0.1                                        |
|   8441 org-gateway   8442 e-control   8443 e2-control          |
|   8444 e-data        8445 e2-data     (8446 upward: U7)        |
|                                                                |
| network org:  org-gateway, org-db, org-migrate                 |
| network e:    e-db, e-migrate, e-control-gateway,              |
|               e-data-gateway, e-backup*, e-restore*            |
| network e2:   e2-db, e2-migrate, e2-control-gateway,           |
|               e2-data-gateway, e2-backup*, e2-restore*         |
| org-internal-e:   org-gateway, e-control-gateway only          |
| org-internal-e2:  org-gateway, e2-control-gateway only         |
|                                                                |
| * under the backup profile; S3 joins no org-internal network   |
+----------------------------------------------------------------+
```

### Text alternative

The host publishes only loopback edges: S1 on 8441, E's S2 on 8442, E2's S2 on 8443, and, new at U6,
**E's S3 on 8444 and E2's S3 on 8445**; U7 takes 8446 upward. Each environment has its own network
holding its store, its migrate service, S2, **S3**, and, under the `backup` profile, its backup and
restore services. The organization level has its own network. Each `org-internal-{env}` network
joins only that environment's S2 and S1. **S3 joins its own environment's network only**, so it
cannot reach the organization level, and no network spans two environments.

## Start-Up Order

| Order | Service | Waits for |
|---|---|---|
| 1 | `{env}-secrets-init` | — (copies into `db/`, `migrate/`, `backup/`, **`restore/`**, `control-gateway/`, **`data-gateway/`**) |
| 2 | `{env}-db` | 1; at first start, its init script creates the **three** roles and sets their passwords |
| 3 | `{env}-migrate` | 1, 2 healthy; applies `0001` to **`0004`** |
| 4 | `{env}-control-gateway` | 1, 3 |
| 4 | **`{env}-data-gateway`** | **1, 3 only**: not `org-gateway`, not `{env}-control-gateway` |

## Volumes and Mounts

| Subdirectory of `{env}-secrets` | Owner | Holds | Mounted by |
|---|---|---|---|
| `db/` | 999 | TLS, superuser, app, migrator, **data** passwords | `{env}-db` |
| `migrate/` | 65532 | migrator password, CA | `{env}-migrate` |
| `backup/` | 999 | migrator password, CA | `{env}-backup` |
| **`restore/`** | 999 | migrator password, CA | **`{env}-restore`** (D-ID-AC-14) |
| `control-gateway/` | 65532 | TLS, CA, app password, human signing key, caller key, log-pseudonym key | `{env}-control-gateway` |
| **`data-gateway/`** | 65532 | TLS, CA, **data password**, **agent signing key**, **counter secret** | **`{env}-data-gateway`** |

Each service mounts only its own subdirectory, read-only, at `/run/secrets` (U4's rule, now checked
under every profile).

## Database Roles in Each Environment Store

| Role | Used by | Privileges on U6's tables |
|---|---|---|
| `soorma_env_migrator` | `{env}-migrate`, backup, restore | Owner |
| `soorma_env_app` | `{env}-control-gateway` | **None** |
| **`soorma_env_data`** | **`{env}-data-gateway`** | As D-ID-AC-07; nothing on `grants`, `credentials`, `schema_migrations`; no `DELETE` |

## When S1 Is Stopped

S3 is unaffected: it neither starts after S1 nor calls it. `pnpm stack:outage`'s Case 3 shows a
running S3, and one restarted while S1 is stopped, serving bootstrap and renewal.

## How U7 Extends It

| U7 adds | Following |
|---|---|
| `{env}-event-ingest`, edges from `127.0.0.1:8446` | D-ID-AC-01, 02 |
| `event-ingest/` with `{env}-agent-verify-key-{n}` only, never a signing key | D-ID-AC-12 |
| S4's own database role, granted in its own migration | D-ID-AC-07's pattern |
| S4 in the Compose-model rules (every profile), `stack:outage`, and `image-packages` | D-ID-AC-13; NP-AC-10 |

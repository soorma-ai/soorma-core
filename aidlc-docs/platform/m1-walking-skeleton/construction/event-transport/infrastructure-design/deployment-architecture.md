# Deployment Architecture: U7 `event-transport`

**Unit**: U7 `event-transport` (soorma-core#10). The local Compose stack (M1-NFR-05) after U7
**Decisions**: [infrastructure-design.md](infrastructure-design.md) (D-ID-ET-01 to 19)

---

## The Stack After U7 (environment E; E2 is the same, with its own ports)

```text
 host loopback only
 127.0.0.1:8441     8442          8444           8446
     |                |             |              |
+----------+   +-----------+  +-----------+  +-----------+
|   org-   |   |    e-     |  |    e-     |  |    e-     |
| gateway  |   |  control- |  |   data-   |  |  event-   |
|   (S1)   |   |  gateway  |  |  gateway  |  |  ingest   |
|          |   |   (S2)    |  |   (S3)    |  |   (S4)    |
+----------+   +-----------+  +-----------+  +-----------+
     |          |       |           |              |
     |          |       +-----------+--------------+
     |          |                   |
  org-internal-e               network e
                                    |
                              +-----------+
                              |   e-db    |
                              | soorma_env|
                              +-----------+
```

*Text alternative*: on the host's loopback, S1 listens on 8441, E's S2 on 8442, E's S3 on 8444,
and E's S4 on 8446 (E2's S2, S3 and S4 on 8443, 8445 and 8447). S1 and E's S2 share the network
`org-internal-e`. E's S2, S3 and S4 and E's store `e-db` share the network `e`. S4 joins only
network `e`: it never reaches S1, S2, S3, or E2. E's fan-out channel lives inside S4's process.

## S4 in Detail

| Aspect | Value |
|---|---|
| Services | `e-event-ingest`, `e2-event-ingest`: **exactly one per environment, no replicas** |
| Image | `soorma/event-ingest:local` (distroless Node 26, pinned by digest) |
| Edge | `127.0.0.1:8446` (E), `8447` (E2) to 8443; TLS 1.3; `event-ingest.{env}.soorma.internal` |
| Health | Loopback 8080 inside the container, on no network |
| Network | `{env}` only |
| Store | `{env}-db` as `soorma_env_ingest` (`verify-full`) |
| Secrets (`/run/secrets`, the `event-ingest/` subpath) | `{env}-event-ingest-tls`, `stack-ca-cert`, `{env}-db-ingest-password`, `{env}-agent-verify-key-1`, `{env}-seal-key-1` |
| Variables | `SOORMA_PROJECT`, `SOORMA_ENVIRONMENT`, `SOORMA_HEALTH_PORT` |
| Memory | `mem_limit: 512m`; S4's measured peak recorded at Code Generation; above 460 MiB, a stop |
| Hardening | User 65532, read-only root, `tmpfs` `/tmp`, every capability dropped, `no-new-privileges` |
| Starts after | `{env}-secrets-init`, `{env}-migrate`; never after S1, S2, or S3 |

## Start-Up Order (per environment)

1. `{env}-secrets-init` copies each secret into its service's subdirectory, then exits
2. `{env}-db` starts; its init script creates the four roles (the migrator, S2's, S3's, S4's)
3. `{env}-migrate` runs `0001` to `0006`
4. `{env}-control-gateway`, `{env}-data-gateway`, `{env}-event-ingest` start, in any order. S4
   checks `JSON.rawJSON` and `synchronous_commit` before it listens

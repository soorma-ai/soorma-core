<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# `@soorma/service-kit`

The organization-neutral runtime that the organization level (S1) and each environment's
services (S2 to S4) share. Nothing in it knows about
principals, material, credentials, or grants; those live in each level's own packages.

It has two entry points:

| Entry                      | What it holds                                                                                                                                                                                                                                                                                                                               | Framework       |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| `@soorma/service-kit`      | The clock; the store (`Store`: a pool of at most 10, a 5-second statement timeout, parameterized SQL from `sql.ts` only) and the migration runner; secret types and constant-time comparison; RFC 8785 canonical JSON; key thumbprints; log pseudonyms; the signed internal request; sign-in verification; the Problem table; the semaphore | None            |
| `@soorma/service-kit/http` | `createAdapter` (Fastify over TLS 1.3, a 16 KiB body limit), `ProblemFilter`, the contract validator, the health listener and healthcheck, and the typed `SecurityLog`                                                                                                                                                                      | NestJS, Fastify |

The root entry imports no framework, so a module such as `@soorma/perimeter` loads none at run
time.

## What a service brings

- **Its own store's migrations and advisory lock key.** `migrate(client, dir, lockKey)` applies
  versioned `NNNN_name.sql` files in order, each in one transaction, recording each file's
  SHA-256. A changed or missing applied migration fails the run. S1 uses `org-identity`'s, each
  environment uses [`env-store`](../env-store/README.md)'s.
- **Its own name for the store**, which errors carry (`org`, `env`). A store error fails closed
  as `unavailable` (503).
- **Its own security events**, as the type parameter of `SecurityLog`. A log line never carries
  a token, a key, or a human identifier: a human is named by `pseudonym(key, reference)`, under
  that level's own key.
- **Its sign-in tolerance**, for `verifySignIn`: S1 verifies its own sign-ins with none; an
  environment allows 30 seconds of clock skew. Verification takes a key source and a sign-in
  status callback, so the same code serves S1 (its own key ring and store) and S2 (S1's
  fetched keys and S1's answer).
- **Its `ProblemFilter` options**: S2 adds `Retry-After: 5` to every 503 and logs the cause.

## Rules it enforces

- SQL only from `sql.ts` constants (`pnpm check:code`)
- Secrets compared only with `secretEqual`, and never with `===` (`pnpm check:code`)
- One Problem table (`PROBLEM_TABLE`): every refusal is a code from it

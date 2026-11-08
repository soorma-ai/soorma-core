# Tech Stack Decisions: U2 `org-identity`

**Unit**: U2 `org-identity` (soorma-core#5)
**Scope**: U2's **runtime** selections, the first in soorma-core. U1's toolchain (U1
tech-stack-decisions T-01 to T-16) applies unchanged, except where T-OI-08 supersedes T-09's
expectation of an SWC transform
**Versions**: checked on the npm registry on 2026-11-08. **Every version below is past U1's
7-day cooldown** (`minimumReleaseAge`; published on or before 2026-11-01). Newer releases
exist inside the cooldown and are not used: `@nestjs/*` 12.4.0 (2026-11-06) and `jose`
6.2.15 and 6.2.16. Exact pins, licences, and transitive counts go into `DEPENDENCIES.md` at
Code Generation

---

## Decisions

| ID | Area | Choice | Version | Licence | Kind | Rationale | Serves |
|---|---|---|---|---|---|---|---|
| T-OI-01 | Framework | **NestJS 12**: `@nestjs/core`, `@nestjs/common`, `@nestjs/platform-fastify`, with the peers `reflect-metadata` and `rxjs`. `class-validator` and `class-transformer` are **not** installed: validation is the contract's Ajv validators (U1 T-05) | 12.3.2; `reflect-metadata` 0.2.2; `rxjs` 7.8.2 | MIT | Runtime | M1-TECH-01. ESM since 12 (U1 T-04) | Q9 A |
| T-OI-02 | HTTP adapter | **Fastify 5**, through `@nestjs/platform-fastify` | `fastify` 5.12.7, as resolved by 12.3.2 | MIT | Runtime, transitive | Lower per-request cost (M1-TECH-03); a body limit set per route (NFR-OI-27) | Q9 A |
| T-OI-03 | Token signing | **`jose`**, JWS with the **fully specified `Ed25519` algorithm (RFC 9864)** only. Verification passes `algorithms: ['Ed25519']`. The key type is fixed to Ed25519 in code. Claims and framing are NFR Design's | 6.2.14 | MIT; 0 dependencies | Runtime | Vetted parsing and algorithm handling instead of hand-written token code | Q10 A |
| T-OI-04 | Cryptography | **Node 26's built-in `node:crypto`**: `argon2` (Argon2id, NFR-OI-11), `scrypt` (the fallback), Ed25519 keys, HMAC-SHA-256 (NFR-OI-05) and HMAC-SHA-1 (TOTP), `randomBytes`, `timingSafeEqual` | Node 26.13.0 (U1 T-01) | — | Runtime, built in | **No dependency** for any primitive. `crypto.argon2` must be **Stable** in Node 26's documentation, or Code Generation stops and asks (NFR-OI-12) | Q6 A; Q3 A; Q4 A |
| T-OI-05 | TOTP | **In-house**, about 40 lines over `node:crypto` HMAC-SHA-1, checked against RFC 6238 Appendix B's vectors | — | — | — | No library is needed for one HMAC and a truncation, and none would remove the replay rule (NFR-OI-08), which needs the store anyway | Q4 A |
| T-OI-06 | Datastore | **PostgreSQL 18**, one database for the organization level | 18.x. The image is pinned by digest at Infrastructure Design | PostgreSQL Licence | Server | ID §10 highest durability; M1-TECH-03 (state outside the process) | Q8 A |
| T-OI-07 | Database access | **`pg`**, plain parameterized SQL, no ORM. `pg-native` is not installed | 8.23.1 | MIT | Runtime | Minimal and explicit (NFR-OI-17); every query visible in review | Q8 A |
| T-OI-08 | Tests for NestJS code | **Vitest 5's default transform**, with **explicit injection tokens** (`@Inject(TOKEN)`) on every constructor parameter, and `emitDecoratorMetadata` off. **No SWC** (`unplugin-swc`, `@swc/core`): this supersedes U1 T-09's expectation | Vitest 5.0.5 (U1) | — | — | Proved by the probe below; one native dependency and its install script avoided | Q9 A |
| T-OI-09 | Build of NestJS packages | **Each NestJS package and service has its own `tsconfig.build.json` that compiles to JavaScript**: `experimentalDecorators` on, `emitDecoratorMetadata` off, `noEmit` off, `erasableSyntaxOnly` off, `allowImportingTsExtensions` off, `outDir` `dist`. Services run the compiled JavaScript. U1's base config (`noEmit`, `erasableSyntaxOnly`) stays as it is for everything else | TypeScript 6.0.3 (U1) | — | — | **Decorators cannot run under Node's type stripping**, which rejects TypeScript-only syntax (proved below) | Q9 condition |
| T-OI-10 | Breached list | **SecLists, top 1,000,000** passwords, as a pinned derived artifact (64-bit SHA-256 prefixes, sorted, 8 MiB) with a manifest | The SecLists commit is pinned at Code Generation | MIT (checked again at Code Generation) | Data | A permissive source; no outside call at run time (NFR-OI-13) | Q7 A |
| T-OI-11 | Logging | **NestJS's built-in `ConsoleLogger` in JSON mode**, to stdout | 12.3.2 | MIT | Runtime | No logging dependency (NFR-OI-22) | Q12 A |
| T-OI-12 | Monitoring definitions | **Alert rules and a dashboard as files** in `deploy/`. The file format is Infrastructure Design's. No monitoring service runs in M1 | — | — | Configuration | SECURITY-14: not applicable in M1, by the user's decision (NFR-OI-24) | Q12 A |

**Lifecycle scripts**: none of T-OI-01 to 03 or T-OI-07 is expected to need one, so the
allowlist stays empty (U1 NFR-WC-16). Code Generation confirms this when it installs them
(`strictDepBuilds` refuses one otherwise).

---

## Probe Records (2026-11-08, isolated scratchpad, Node 26.13.0)

### Q9: explicit injection tokens under Vitest's default transform

Installed with `--ignore-scripts`: `@nestjs/core`, `@nestjs/common`,
`@nestjs/platform-fastify` (first 12.4.0, then **re-run at 12.3.2**, the version past the
cooldown), `reflect-metadata` 0.2.2, `rxjs` 7.8.2, `vitest` 5.0.5, `typescript` 6.0.3,
`@types/node` 26.6.6. The module: a provider with `constructor(@Inject(CLOCK) …)` where
`CLOCK` is a `Symbol`, and a Fastify controller with `@Inject(Greeter)`.

| Check | Result |
|---|---|
| Vitest 5.0.5, **no config file** (the default transform), `experimentalDecorators` in `tsconfig.json`, `emitDecoratorMetadata` off: boot the module, call the provider, `GET /probe` through Fastify's `inject` | **Pass**: injection by token works; 200 with the expected body |
| `tsc --noEmit` over source and tests | **Pass** |
| `tsc -p tsconfig.build.json` (emit to `dist/`), then `node dist/main.js` | **Pass**: 200 with the expected body |
| Control: the decorated source run directly by Node (type stripping) | **Fails**, as expected: `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` (a parameter property is not supported in strip-only mode). Hence T-OI-09 |
| Control: the same controller **without** `@Inject` (type-based injection) under the default transform | **Fails**, as expected: 500. The tokens, not decorator metadata, make injection work. Hence T-OI-08 |

### Q10: `jose` and RFC 9864

| Check (`jose` 6.2.16, then **re-run at 6.2.14**) | Result |
|---|---|
| Sign with `alg: 'Ed25519'` and a Node Ed25519 key; verify with `algorithms: ['Ed25519']` | **Pass**; the protected header reads `Ed25519` |
| A token signed with `alg: 'EdDSA'`, verified with `algorithms: ['Ed25519']` | Refused: `ERR_JOSE_ALG_NOT_ALLOWED` |
| Sign with `alg: 'Ed25519'` and a P-256 key | Refused |

### Q6: `crypto.argon2`

Argon2id, 64 MiB, 3 passes, parallelism 1, 32-byte tag: **169 ms**; no experimental warning
printed. **The stability index is checked at Code Generation, not here** (NFR-OI-12).

---

## Not Decided Here

| Selection | Decided at |
|---|---|
| Token claims, key ids, rotation; the TOTP seed cipher; the internal caller credential's mechanism | U2 NFR Design |
| PostgreSQL image, TLS, configuration and secret delivery, the alert-rule file format | U2 Infrastructure Design |
| The environment store | U4 NFR Requirements (PostgreSQL is the likely choice, for one engine across the stack) |

## Stages for U2 After This One

| Stage | Decision | Reason |
|---|---|---|
| NFR Design | **Run** | Token format and keys; seed encryption; the internal caller credential; the slot row layout; the error handler; request ids |
| Infrastructure Design | **Run** | The first deployable and datastore: `deploy/local/`, PostgreSQL, secret and enrollment-material delivery (M1-TECH-06), TLS, monitoring files |
| QA construction enrichment | **Run** after Infrastructure Design | qa-test-cases.md §2.6 |
| Construction Design PR gate | **Run** after enrichment | pr-checkpoint.md Section 5 |
| Code Generation | **Run** after the gate | Always |

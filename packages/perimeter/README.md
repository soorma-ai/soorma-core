<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# `@soorma/perimeter` (P1)

The perimeter's shared checks, and **the one place soorma-core turns a refusal into an RFC 9457
Problem**.

- **Presenter checks**: classifying and verifying the credential a request presents (S1 today).
- **The Problem table**: every code in [`contract/conventions/errors.md`](../../contract/conventions/errors.md),
  with its status and a generic title. A test keeps it equal to the convention.
- **The contract version**: `CONTRACT_VERSION` and the accepted set `SUPPORTED_VERSIONS`, defined
  once.

## Emitting a Problem

`problemResponse(refusal, requestId)` returns `{ status, headers, body }` and imports no framework.
A surface keeps only a thin adapter: S1's `sendProblem` in `services/org-gateway/src/http.ts` is
the Fastify one.

Every Problem carries:

- `type`: `urn:soorma:problem:{code}`
- `title`, `status`, and `code`
- `instance`: `urn:soorma:request:{request id}`

The headers are `Content-Type: application/problem+json; charset=utf-8`, `Soorma-Contract-Version`,
and `Soorma-Request-Id`. A 401 adds `WWW-Authenticate: Bearer`, and a 429 or 503 adds
`Retry-After`, at least 1.

## The rule for every edge

**Every edge runs `assertProblem` on every Problem it emits.** S1 does so now. S2, S3, and S4 do
so at U4, U6, and U7.

```ts
import { assertProblem } from '@soorma/perimeter/testing';

assertProblem(response, { status: 403, code: 'forbidden' });
```

`@soorma/perimeter/testing` is test-only. Its file is outside `src/`, so no build emits it, and
its export carries only the `source` condition, so Node cannot load it at run time. It checks:

- the status, the Soorma headers, and the content type
- the `urn:soorma:` forms, with `instance` matching `Soorma-Request-Id`
- `WWW-Authenticate` exactly on a 401, and `Retry-After` exactly on a 429 or 503
- `supportedVersions` on `unsupported_contract_version`
- the contract's `Problem` schema

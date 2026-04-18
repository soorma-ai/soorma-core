# Shared Example Auth Helper

`examples.shared.auth` is a lightweight developer bootstrap helper for Soorma examples and developer-owned backends.

It gives you a simple trusted auth proxy pattern when you want to talk to secured Soorma services without first building a full user identity system, bootstrap service, or session-management stack.

## When It Fits

This helper is a good fit for:
- local development
- examples and tutorials
- integration tests and internal demos
- single-operator systems
- developer-owned backend services that intentionally act as the trusted principal for their own application

This helper is not a replacement for:
- end-user login and session management
- multi-user identity lifecycle
- delegated user auth flows
- public production auth boundaries

Use it when your application backend can safely act as the trusted caller for Soorma infrastructure and you want to postpone full user identity management until you actually need it.

## What It Does

The helper wraps a small but useful identity bootstrap flow:
- onboards a platform tenant and bootstrap admin principal through identity-service
- persists the onboarding payload under `.soorma/*-identity.json`
- requests, caches, and refreshes bearer tokens for the bootstrap admin principal
- exports the token and platform tenant context into environment variables for subprocess compatibility
- surfaces recovery instructions when persisted onboarding state is stale or invalid

## Superuser Key Coordination

For onboarding, the helper must present the same superuser API key that the target identity-service deployment is configured to accept.

In the local Soorma stack this works automatically because both sides use the same local default:

```bash
IDENTITY_SUPERUSER_API_KEY=dev-identity-admin
```

If you deploy identity-service with a different superuser key, you must provide that same value to the process using `examples.shared.auth`.

In practice, that means:
- set `IDENTITY_SUPERUSER_API_KEY` on the identity-service deployment
- set the same `IDENTITY_SUPERUSER_API_KEY` on the developer auth proxy, example runner, or developer-owned backend that calls onboarding

The helper reaches onboarding through `IdentityServiceClient`, which resolves its superuser onboarding credential from `IDENTITY_SUPERUSER_API_KEY` and then falls back to the legacy alias `IDENTITY_ADMIN_API_KEY` for local compatibility.

If those values do not match what identity-service expects, onboarding will fail with `403`.

## Basic Usage

```python
from examples.shared.auth import build_example_token_provider

token_provider = build_example_token_provider("my-app", __file__)
```

You can pass the provider directly into Soorma clients that support `auth_token_provider`, or you can eagerly provision auth state:

```python
from examples.shared.auth import ensure_example_auth_token

token = await ensure_example_auth_token("my-app", __file__)
```

The provider also exposes the bootstrapped identifiers when your app needs them:

```python
tenant_id = await token_provider.get_platform_tenant_id()
principal_id = await token_provider.get_bootstrap_admin_principal_id()
```

## Recovery Behavior

If the persisted onboarding payload is stale, incomplete, or backed by an invalid tenant-admin credential, the helper raises a recovery-oriented error instead of leaving the developer guessing.

The recovery path is to delete the cached bootstrap files and rerun:

```bash
rm .soorma/*-identity.json
```

The next run will re-onboard the example or developer-owned backend and persist fresh identity state.

## Relationship To Identity Service

Identity-service remains the authority for:
- tenant onboarding
- bootstrap admin principal creation
- tenant-admin credential issuance
- JWT issuance

This helper is just a thin developer-side broker around those flows. It makes the identity-service bootstrap path easier to consume in simple apps, but it does not replace identity-service itself.

For identity-service route details and credential lifecycle behavior, see [services/identity-service/README.md](../../services/identity-service/README.md).
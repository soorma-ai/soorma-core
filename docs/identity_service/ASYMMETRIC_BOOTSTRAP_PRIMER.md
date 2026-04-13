# Asymmetric JWT Bootstrap Primer (Local Soorma Stack)

**Audience:** Developers running `soorma dev` locally
**Scope:** Unit 3 compatibility phase (RS256 issuer + JWKS verification)

## 1. Quick Answer

Today, `soorma dev` does not auto-generate RSA keypairs for you.

It can bootstrap a deterministic local stack, but asymmetric mode still requires providing signing/verification material via environment variables.

This primer gives a copy-paste workflow so you can run RS256 + JWKS mode reliably.

## 2. What You Will Configure

You need four categories of settings:

1. Identity-service issuer signing settings (private/public key + active `kid`)
2. Verifier settings for all services using `soorma-service-common` middleware
3. Issuer trust and audience settings
4. `soorma dev` bootstrap/restart workflow to avoid drift failures

## 3. Generate Local RSA Keys

Run from repository root (`soorma-core`):

```bash
mkdir -p .soorma/keys

openssl genpkey \
  -algorithm RSA \
  -pkeyopt rsa_keygen_bits:2048 \
  -out .soorma/keys/identity-signing-private.pem

openssl rsa \
  -in .soorma/keys/identity-signing-private.pem \
  -pubout \
  -out .soorma/keys/identity-signing-public.pem
```

## 4. Convert PEMs to Environment-Safe Values

Docker compose `.env` values are single-line strings. Convert PEM files to escaped-newline strings:

```bash
escape_pem() {
  awk 'NF {sub(/\r/, ""); printf "%s\\n", $0;}' "$1"
}

export IDENTITY_SIGNING_PRIVATE_KEY_PEM="$(escape_pem .soorma/keys/identity-signing-private.pem)"
export IDENTITY_SIGNING_PUBLIC_KEY_PEM="$(escape_pem .soorma/keys/identity-signing-public.pem)"
```

## 5. Set RS256/JWKS Environment Variables

Use this exact baseline before `soorma dev --start`:

```bash
# Issuer signing mode
export IDENTITY_SIGNING_ALGORITHM=RS256
export IDENTITY_SIGNING_KEY_ID=local-rs1
export IDENTITY_ACTIVE_SIGNING_KID=local-rs1
export IDENTITY_SIGNING_PRIVATE_KEY_PEM="$IDENTITY_SIGNING_PRIVATE_KEY_PEM"
export IDENTITY_SIGNING_PUBLIC_KEY_PEM="$IDENTITY_SIGNING_PUBLIC_KEY_PEM"

# Keep issuer claim/trust aligned with current token issuance behavior
export SOORMA_AUTH_JWT_ISSUER=soorma-identity-service
export SOORMA_AUTH_JWT_AUDIENCE=soorma-services

# Middleware verifier primary source (inside docker network)
export SOORMA_AUTH_JWKS_URL=http://identity-service:8085/v1/identity/.well-known/jwks.json
export SOORMA_AUTH_OPENID_CONFIGURATION_URL=http://identity-service:8085/v1/identity/.well-known/openid-configuration

# Optional bounded fallback verifier key (recommended during compatibility)
export SOORMA_AUTH_JWT_PUBLIC_KEY_ID=local-rs1
export SOORMA_AUTH_JWT_PUBLIC_KEY_PEM="$IDENTITY_SIGNING_PUBLIC_KEY_PEM"

# Optional cache tuning
export SOORMA_AUTH_JWKS_CACHE_TTL_SECONDS=300
```

## 6. Start or Recreate the Stack

If this is your first run:

```bash
soorma dev --start
```

If you already started with different JWT settings and get drift protection failures, reset first:

```bash
soorma dev --stop --clean
soorma dev --start
```

## 7. Variable-by-Variable Mapping

| Variable | Purpose | Consumed By |
|---|---|---|
| `IDENTITY_SIGNING_ALGORITHM` | selects signing algorithm (`RS256`) | identity-service provider facade |
| `IDENTITY_SIGNING_KEY_ID` | default signing `kid` | identity-service provider facade |
| `IDENTITY_ACTIVE_SIGNING_KID` | active signing key selector | identity-service provider facade |
| `IDENTITY_SIGNING_PRIVATE_KEY_PEM` | RS256 private key for issuance | identity-service provider facade |
| `IDENTITY_SIGNING_PUBLIC_KEY_PEM` | RS256 public key for JWKS/static fallback | identity-service provider facade |
| `SOORMA_AUTH_JWKS_URL` | JWKS primary verifier source | all services using `soorma-service-common` middleware |
| `SOORMA_AUTH_OPENID_CONFIGURATION_URL` | discovery metadata (issuer/jwks_uri) | all services using `soorma-service-common` middleware |
| `SOORMA_AUTH_JWT_ISSUER` | explicit trusted issuer | all services using `soorma-service-common` middleware |
| `SOORMA_AUTH_JWT_AUDIENCE` | JWT audience check | all services using `soorma-service-common` middleware |
| `SOORMA_AUTH_JWT_PUBLIC_KEY_PEM` + `SOORMA_AUTH_JWT_PUBLIC_KEY_ID` | static fallback verifier key | all services using `soorma-service-common` middleware |
| `SOORMA_AUTH_JWKS_CACHE_TTL_SECONDS` | discovery/JWKS cache TTL | all services using `soorma-service-common` middleware |

## 8. Verify It Is Actually Running Asymmetric Mode

### 8.1 Verify discovery endpoints

```bash
curl -s http://localhost:8085/v1/identity/.well-known/openid-configuration | jq
curl -s http://localhost:8085/v1/identity/.well-known/jwks.json | jq
```

You should see `RS256` and at least one key with `kid=local-rs1`.

### 8.2 Verify shared middleware JWT validation path

Run shared library tests:

```bash
PYTHONPATH=libs/soorma-service-common/src:libs/soorma-common/src \
  .venv/bin/python -m pytest \
  libs/soorma-service-common/tests/test_middleware.py \
  libs/soorma-service-common/tests/test_dependencies.py
```

### 8.3 Verify identity-service crypto/discovery tests

```bash
PYTHONPATH=services/identity-service/src:libs/soorma-common/src:libs/soorma-service-common/src \
  .venv/bin/python -m pytest \
  services/identity-service/tests/test_provider_facade.py \
  services/identity-service/tests/test_discovery_api.py
```

## 9. Known Local Compatibility Notes

1. This is Unit 3 compatibility phase. Some paths still retain bounded legacy fallback behavior by design.
2. `soorma dev` currently seeds symmetric defaults unless you override as shown above.
3. If you change any bootstrap-affecting JWT config, drift protection can trigger `FAILED_DRIFT`; use `--stop --clean` before restart.

## 10. Recommended Next CLI Improvement

To fully eliminate manual exports, add a `soorma dev` asymmetric bootstrap mode that:

1. generates local RSA keypair under `.soorma/keys/`
2. writes escaped PEM vars to `.soorma/.env`
3. sets RS256 + JWKS/discovery defaults automatically
4. includes generated key fingerprints in bootstrap-state drift checks

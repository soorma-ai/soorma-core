# Asymmetric JWT Bootstrap Primer (Local Soorma Stack)

**Audience:** Developers running `soorma dev` locally
**Scope:** Unit 4 cutover hardening (`soorma dev` RS256/JWKS bootstrap defaults)

## 1. Quick Answer

`soorma dev` now bootstraps a persisted local RS256 keypair and inline JWKS verifier config by default.

You only need manual overrides when you want to test alternate key material or simulate key rotation.

This primer explains the default behavior and the override path.

## 2. What You Will Configure

You need four categories of settings when overriding the defaults:

1. Identity-service issuer signing settings (private/public key + active `kid`)
2. Verifier settings for all services using `soorma-service-common` middleware
3. Issuer trust and audience settings
4. `soorma dev` bootstrap/restart workflow to avoid drift failures

## 3. Default `soorma dev` Behavior

When you run `soorma dev --start`, the CLI creates `.soorma/identity/` on first use and persists:

1. `.soorma/identity/identity-signing-private.pem`
2. `.soorma/identity/identity-signing-public.pem`
3. `.soorma/identity/identity-jwks.json`

The generated `.soorma/.env` then includes:

1. `IDENTITY_SIGNING_ALGORITHM=RS256`
2. `IDENTITY_ACTIVE_SIGNING_KID=dev-rs256`
3. `IDENTITY_SIGNING_PRIVATE_KEYRING_JSON` derived from the persisted private key
4. `IDENTITY_SIGNING_PUBLIC_KEYRING_JSON` derived from the persisted public key
5. Inline `IDENTITY_JWKS_PUBLICATION_JSON` and `SOORMA_AUTH_JWKS_JSON` derived from the persisted JWKS file
6. Static `SOORMA_AUTH_JWT_PUBLIC_KEYS_JSON` fallback derived from the persisted public key

That means the local stack starts in RS256/JWKS mode without extra shell setup and reuses the same keypair across runs until you delete it.

To rotate the local keypair, delete the files under `.soorma/identity/` and run `soorma dev` again.

## 4. Generate Alternate Local RSA Keys

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

## 5. Convert PEMs to Environment-Safe JSON Keyrings

Docker compose `.env` values are single-line strings. Build JSON keyrings so PEM newlines survive parsing cleanly:

```bash
python - <<'PY'
import json
from pathlib import Path

private_pem = Path('.soorma/keys/identity-signing-private.pem').read_text()
public_pem = Path('.soorma/keys/identity-signing-public.pem').read_text()

print('export IDENTITY_SIGNING_PRIVATE_KEYRING_JSON=' + json.dumps(json.dumps({'local-rs1': private_pem})))
print('export IDENTITY_SIGNING_PUBLIC_KEYRING_JSON=' + json.dumps(json.dumps({'local-rs1': public_pem})))
PY
```

## 6. Set RS256/JWKS Override Variables

Use this exact baseline before `soorma dev --start`:

```bash
# Issuer signing mode
export IDENTITY_SIGNING_ALGORITHM=RS256
export IDENTITY_ACTIVE_SIGNING_KID=local-rs1
export IDENTITY_SIGNING_PRIVATE_KEYRING_JSON="$IDENTITY_SIGNING_PRIVATE_KEYRING_JSON"
export IDENTITY_SIGNING_PUBLIC_KEYRING_JSON="$IDENTITY_SIGNING_PUBLIC_KEYRING_JSON"

# Keep issuer claim/trust aligned with current token issuance behavior
export SOORMA_AUTH_JWT_ISSUER=soorma-identity-service
export SOORMA_AUTH_JWT_AUDIENCE=soorma-services

# Inline JWKS for issuer publication and verifier startup determinism
export IDENTITY_JWKS_PUBLICATION_JSON='{"keys":[...]}'
export IDENTITY_VERIFIER_JWKS_JSON="$IDENTITY_JWKS_PUBLICATION_JSON"
export SOORMA_AUTH_JWKS_JSON="$IDENTITY_JWKS_PUBLICATION_JSON"
export SOORMA_AUTH_JWT_PUBLIC_KEYS_JSON="$IDENTITY_SIGNING_PUBLIC_KEYRING_JSON"

# Optional cache tuning
export SOORMA_AUTH_JWKS_CACHE_TTL_SECONDS=300
```

## 7. Start or Recreate the Stack

If this is your first run:

```bash
soorma dev --start
```

If you already started with different JWT settings and get drift protection failures, reset first:

```bash
soorma dev --stop --clean
soorma dev --start
```

## 8. Variable-by-Variable Mapping

| Variable | Purpose | Consumed By |
|---|---|---|
| `IDENTITY_SIGNING_ALGORITHM` | selects signing algorithm (`RS256`) | identity-service provider facade |
| `IDENTITY_ACTIVE_SIGNING_KID` | active signing key selector | identity-service provider facade |
| `IDENTITY_SIGNING_PRIVATE_KEYRING_JSON` | RS256 private signing keyring | identity-service provider facade |
| `IDENTITY_SIGNING_PUBLIC_KEYRING_JSON` | RS256 public publication keyring | identity-service provider facade |
| `IDENTITY_JWKS_PUBLICATION_JSON` | published JWKS payload | identity-service provider facade and discovery routes |
| `IDENTITY_VERIFIER_JWKS_JSON` | delegated verifier JWKS input | identity-service provider facade |
| `SOORMA_AUTH_JWKS_JSON` | JWKS primary verifier source | all services using `soorma-service-common` middleware |
| `SOORMA_AUTH_JWT_ISSUER` | explicit trusted issuer | all services using `soorma-service-common` middleware |
| `SOORMA_AUTH_JWT_AUDIENCE` | JWT audience check | all services using `soorma-service-common` middleware |
| `SOORMA_AUTH_JWT_PUBLIC_KEYS_JSON` | static fallback verifier keyring | all services using `soorma-service-common` middleware |
| `SOORMA_AUTH_JWKS_CACHE_TTL_SECONDS` | discovery/JWKS cache TTL | all services using `soorma-service-common` middleware |

## 9. Verify It Is Actually Running Asymmetric Mode

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

1. Some bounded compatibility seams remain in persistence and migration surfaces; this primer only covers local JWT bootstrap behavior.
2. If you change any bootstrap-affecting JWT config, drift protection can trigger `FAILED_DRIFT`; use `--stop --clean` before restart.
3. Deleting `.soorma/identity/` is the intended local rotation path for the generated keypair.

## 10. Recommended Next CLI Improvement

Manual exports are only needed when you want custom key material or a custom verifier source.

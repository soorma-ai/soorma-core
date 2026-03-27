# Build Instructions

## Prerequisites
- Build Tool: Python 3.12+, pip, pytest
- Environment: repo-root virtual environment (`.venv`)
- Services for integration tests: PostgreSQL, NATS, service-specific local runners as needed
- Recommended OS: macOS or Linux

## Build Steps

### 1. Activate environment
```bash
cd /Users/amit/ws/github/soorma-ai/soorma-core
source .venv/bin/activate
```

### 2. Install editable packages
```bash
pip install -e libs/soorma-common
pip install -e libs/soorma-service-common
pip install -e services/registry
pip install -e services/memory
pip install -e services/tracker
pip install -e services/event-service
pip install -e sdk/python
```

### 3. Verify package import/build integrity
```bash
python -m pip check
python -c "import soorma_common, soorma_service_common, soorma; print('imports ok')"
```

### 4. Validate formatting/lint (optional but recommended)
```bash
# Run only if configured in your environment
# ruff check .
# black --check .
```

## Build Success Criteria
- All editable installs complete without dependency resolution errors.
- `pip check` reports no broken requirements.
- Package imports succeed for `soorma_common`, `soorma_service_common`, and `soorma`.

## Troubleshooting

### Dependency resolution errors
- Cause: stale virtualenv or mismatched package versions.
- Fix: recreate `.venv`, reinstall editable packages in sequence above.

### Import errors after install
- Cause: missing editable install for one unit package.
- Fix: rerun the relevant `pip install -e <path>` command and re-check imports.

### Test collection import-path errors at repo root
- Cause: running broad `pytest -q` from repo root can hit package-relative `tests.*` import assumptions.
- Fix: run test suites from package roots (instructions in unit-test-instructions.md).

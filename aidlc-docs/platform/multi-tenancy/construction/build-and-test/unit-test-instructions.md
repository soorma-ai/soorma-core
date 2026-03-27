# Unit Test Execution

## Purpose
Execute unit-level validation for all units delivered in this initiative (U1-U7).

## 1. Activate environment
```bash
cd /Users/amit/ws/github/soorma-ai/soorma-core
source .venv/bin/activate
```

## 2. Execute package-level test suites
Run from each package root to avoid repo-root import-path collection issues.

### U1 - libs/soorma-common
```bash
cd libs/soorma-common
python -m pytest tests/ --tb=short -q
```

### U2 - libs/soorma-service-common
```bash
cd /Users/amit/ws/github/soorma-ai/soorma-core/libs/soorma-service-common
python -m pytest tests/ --tb=short -q
```

### U3 - services/registry
```bash
cd /Users/amit/ws/github/soorma-ai/soorma-core/services/registry
python -m pytest tests/ --tb=short -q
```

### U4 - services/memory
```bash
cd /Users/amit/ws/github/soorma-ai/soorma-core/services/memory
python -m pytest tests/ --tb=short -q
```

### U5 - services/tracker
```bash
cd /Users/amit/ws/github/soorma-ai/soorma-core/services/tracker
python -m pytest tests/ --tb=short -q
```

### U7 - services/event-service
```bash
cd /Users/amit/ws/github/soorma-ai/soorma-core/services/event-service
python -m pytest tests/ --tb=short -q
```

### U6 - sdk/python
```bash
cd /Users/amit/ws/github/soorma-ai/soorma-core/sdk/python
python -m pytest tests/ --tb=short -q
```

## 3. Expected outcomes
- Prior validated baseline from construction:
  - U1: 112/112 passed
  - U2: 40/40 passed
  - U3: 80/80 passed
  - U5: 21/21 passed
  - U7: 27/27 passed
  - U6: 506 passed, 5 skipped
- U4 memory service test gate previously passed in local run context.

## 4. Failure handling
1. Capture failing command and traceback.
2. Confirm the package is installed editable in `.venv`.
3. Re-run only failed module first, then full package tests.
4. Update `aidlc-state.md` and `audit.md` with failure details if unresolved.

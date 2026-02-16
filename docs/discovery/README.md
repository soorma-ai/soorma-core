# Service Discovery

**Status:** 📋 Planned  
**Last Updated:** February 15, 2026  
**Related Stages:** Stage 5 (Discovery & A2A)

---

## Overview

[How agents find each other and capabilities]

## Registration

[Agent startup registration, capability declaration, EventDefinition registration]

## Discovery Patterns

### 1. Static Discovery

[Hardcoded event names]

### 2. Dynamic Discovery

[Registry query at runtime]

### 3. LLM-based Selection

[EventSelector utility]

## EventSelector Utility

[LLM-driven event selection, customizable prompts, registry validation]

## Examples

- [07-tool-discovery](../../examples/07-tool-discovery/) - Dynamic capability discovery
- [09-app-research-advisor](../../examples/09-app-research-advisor/) - Uses EventSelector

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Technical design and implementation
- [Registry Service](../../services/registry/README.md) - Service implementation
- [Refactoring Plan](../refactoring/sdk/07-DISCOVERY.md) - Stage 5 refactoring details

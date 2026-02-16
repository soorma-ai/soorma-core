# Documentation Archive

**Last Updated:** February 15, 2026

This directory contains legacy documentation files that have been migrated to the new feature-scoped structure.

---

## Migration Summary

As part of the documentation organization effort (February 2026), adhoc documentation files were reorganized into feature-specific areas following the structure defined in [AGENT.md](../../AGENT.md).

### Where Content Moved

| Old File | New Location | Description |
|----------|-------------|-------------|
| `DESIGN_PATTERNS.md` | [docs/agent_patterns/](../agent_patterns/) | Agent models (Tool, Worker, Planner), DisCo pattern |
| `EVENT_PATTERNS.md` | [docs/event_system/](../event_system/) | Event-driven architecture, topics, messaging |
| `MEMORY_PATTERNS.md` | [docs/memory_system/](../memory_system/) | CoALA memory framework (4 memory types) |
| `MESSAGING_PATTERNS.md` | [docs/event_system/](../event_system/) | Queue/broadcast/load-balancing patterns |
| `TOPICS.md` | [docs/event_system/](../event_system/) | Fixed topic definitions |

---

## New Documentation Structure

Documentation is now organized by feature area:

```
docs/
├── agent_patterns/       # Tool, Worker, Planner models
│   ├── README.md         # User guide & patterns
│   └── ARCHITECTURE.md   # Technical architecture
├── event_system/         # Event-driven architecture
│   ├── README.md         # Topics, messaging patterns
│   └── ARCHITECTURE.md   # Event Service & SDK design
├── memory_system/        # CoALA memory framework
│   ├── README.md         # Memory types & patterns
│   └── ARCHITECTURE.md   # Memory Service design
├── discovery/            # Registry & capability discovery
│   ├── README.md         # Discovery patterns
│   └── ARCHITECTURE.md   # Registry Service design
└── gateway/              # HTTP/REST API (DRAFT)
    ├── README.md         # Gateway patterns
    ├── ARCHITECTURE.md   # Gateway design
    └── plans/            # Design planning docs
```

Each feature area follows the pattern:
- **README.md**: User guide with examples and best practices
- **ARCHITECTURE.md**: Technical design and implementation details
- **plans/**: Planning documents for future work

---

## Why This Archive Exists

These files are preserved for:
1. **Historical reference** - Track evolution of documentation
2. **Link stability** - Some external references may still point to old locations
3. **Content verification** - Confirm all content was migrated correctly

---

## Using New Documentation

For current documentation, always use the feature-scoped structure:

- **Agent patterns**: [docs/agent_patterns/README.md](../agent_patterns/README.md)
- **Event system**: [docs/event_system/README.md](../event_system/README.md)
- **Memory system**: [docs/memory_system/README.md](../memory_system/README.md)
- **Discovery**: [docs/discovery/README.md](../discovery/README.md)

For architecture overview: [ARCHITECTURE.md](../../ARCHITECTURE.md)

---

## Notes

- These archived files are **read-only** - do not update them
- All future documentation updates go to feature-scoped areas
- This archive may be removed in a future release once all references are updated

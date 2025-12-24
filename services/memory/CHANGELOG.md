# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.1] - 2025-12-24

### Changed
- Bumped version to 0.5.1 to align with unified platform release

## [0.5.0] - 2025-12-23

### Added
- Initial release of Memory Service for Soorma platform
- CoALA (Cognitive Architectures for Language Agents) framework implementation
- Four memory types: Working, Episodic, Semantic, and Procedural
- PostgreSQL with pgvector for semantic search capabilities
- Row Level Security (RLS) for native multi-tenancy isolation
- Tenant and user replica tables for data integrity
- Automatic embedding generation via OpenAI API
- REST API endpoints for all memory operations
- Local development mode with default tenant
- Production-ready multi-tenant authentication middleware
- HNSW indexes for high-performance vector search
- Comprehensive API documentation
- Docker Compose integration via soorma dev CLI

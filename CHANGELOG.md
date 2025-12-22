# Changelog

All notable changes to the Soorma Core project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Multi-provider LLM support in research-advisor example via `llm_utils.py`
  - Automatic model selection based on available API keys
  - Support for OpenAI, Anthropic, Google/Gemini, Azure, Together AI, and Groq
  - `get_llm_model()` and `has_any_llm_key()` helper functions

### Changed
- Updated research-advisor example agents to use dynamic model selection
  - `advisor.py`: Now uses `get_llm_model()` instead of hardcoded GPT-4.1-nano
  - `planner.py`: Now uses `get_llm_model()` instead of hardcoded GPT-4.1-nano
  - `researcher.py`: Now uses `get_llm_model()` instead of hardcoded GPT-4.1-nano
  - `validator.py`: Now uses `get_llm_model()` instead of hardcoded GPT-4.1-nano
- Major refactor of `planner.py` for autonomous choreography
  - Removed hardcoded workflow rules
  - Implemented LLM reasoning over dynamically discovered event metadata
  - Added circuit breakers (max actions limit, vague result detection)
  - Improved prompt engineering for autonomous agent orchestration
- Updated README.md with comprehensive documentation on:
  - Autonomous choreography vs traditional orchestration
  - LLM reasoning engine approach
  - Circuit breaker patterns
  - Multi-provider LLM configuration
- Updated ARCHITECTURE.md with deep technical details on:
  - Why to avoid hardcoded workflow rules
  - DisCo protocol implementation
  - Prompt engineering strategies
  - Circuit breaker implementations
  - Future Tracker service plans

### Fixed
- Infinite loop issues in planner (research → draft → research cycles)
- Payload mismatches in validation requests (`research_context` → `source_text`)
- Vague result detection preventing meta-descriptions instead of actual content
- LLM skipping required workflow steps (validation before completion)

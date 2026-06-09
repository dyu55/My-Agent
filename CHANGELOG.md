# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-06-08

### Added
- Dual-model support: separate think/execute models
- Task interruption recovery (checkpoint save/resume)
- Dry-run preview mode
- Cost/step/time limits
- Trajectory serialization for debugging
- File change memory across subtasks
- JSON parsing robustness for small models
- Error recovery context in execution summary
- CONVENTIONS.md auto-loading
- Structured conversation memory compression
- Edit failure file content snippet
- Empty response early detection
- Non-JSON response code extraction
- GitHub Actions CI pipeline
- Version info (--version flag)
- pyproject.toml for modern packaging
- Makefile for common tasks
- .editorconfig for consistent style
- CONTRIBUTING.md guidelines
- MIT LICENSE

### Changed
- LLM cache uses batched disk writes
- Prompt normalization for better cache hits
- FallbackStrategy reuses response for regex extraction
- System prompt deduplication
- Project context caching
- Handler dictionary caching in executor
- Reflector analysis on single-task fast-path

### Fixed
- Ollama connection error friendly message
- Write verification after file creation

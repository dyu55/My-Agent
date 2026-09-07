# Tool execution refactoring — 2026-09-06

## Changes

- Extracted shared action/result dataclasses into `agent/actions.py` and introduced `agent/tools/registry.py` for explicit payload dispatch and lazy tool construction.
- Removed the executor's duplicate file, process, search and Git implementations. Tool modules now own side effects; the executor applies policy, reports diagnostics and records every attempt.
- Replaced output-prefix guessing with structured success/error propagation. Nonzero shell exits, failed pytest runs, empty error output and mixed batch-write outcomes cannot silently become successes.
- Replaced pytest terminal-output guessing with unique JUnit reports and process exit codes. Collection errors and no-tests-collected results are failures. Subprocesses use the active Python interpreter.
- Unified file and directory path checks, rejecting sibling-prefix and symlink escapes. Batch writes use the same file implementation, protected-path checks and rollback behavior as individual writes.
- Completed package discovery for CLI, skills, MCP, wiki and memory, and added the installed `myagent` command. Runtime requirements have one source; ChromaDB is available through the `memory` extra.
- Made external-service tests opt-in with `--run-live`; ordinary collection no longer imports credentials from `.env` through the manual test scripts.
- Converted boolean-returning check scripts into asserting pytest wrappers. This exposed a previously hidden failure in generated parameter documentation. Fixed its command-line spelling and invalid hyphenated Python module imports in test scaffolds.

## Compatibility

The public `Action`, `ExecutionResult`, `ExecutionStatus` and `ToolExecutor` imports from `agent.executor` are retained. Existing command names and file-edit syntax diagnostics remain available. Private duplicate executor helpers were removed; extensions should register handlers with `executor.registry.register(name, handler)` and return `ToolResult`.

Batch writes retain successful files and report failure if another item fails. Workspace path checks cover file tools; arbitrary shell commands remain subject to the agent's tool policy, not a new operating-system sandbox.

## Local validation

Environment: macOS arm64, Python 3.12.13.

| Check | Observed result |
| --- | --- |
| Original baseline with the prior service-test exclusions | 474 passed, 1 skipped |
| Refactored suite | 494 passed, 40 skipped, 44.86 seconds |
| New execution-contract tests | 24 passed |
| Coverage of agent/utils | 54% |
| Existing blocking syntax/undefined-name checks | Passed |
| Source distribution and wheel | Built successfully |
| Clean wheel installation outside checkout | CLI help and all included module groups imported successfully |

Of the 40 skips, 39 require external model/embedding services and one requires the optional Anthropic SDK. Baseline counts included four manual check functions whose returned booleans did not determine pytest success; the new count must not be interpreted as an equivalent live-model verification. No live-model quality, performance benchmark, paid API completion, or optional vector-memory integration is claimed.

Reproduce with `python -m pip install -e ".[dev]"`, `python -m pytest`, and `python -m build`. After configuring the required external services, install `.[memory]` and run `python -m pytest --run-live -m live` separately.

# Runtime architecture

The package separates schemas, provider protocol adapters, the execution engine, tools, workspace file operations, and persistent storage. The CLI owns explicit permissions and model selection. The browser viewer is read-only; it cannot start a tool or edit a file.

## Run lifecycle

`pending → running → succeeded | paused | failed`; file restoration moves a run to `reverted`.

The planner proposes a dependency graph with unique IDs and no cycles. Proposed execution state is discarded. The engine chooses a ready step and requests one action. It checks permissions, persists the action intent, calls the typed tool handler, saves its structured result, and asks for a reflection before completing a step. A failed tool remains unresolved until that tool succeeds. Mutation invalidates verification; a passing pytest run after the latest mutation is required for completion.

SQLite stores checkpoints and ordered events. A nonblocking per-run file lock prevents concurrent resumes on macOS/Linux. Calls and elapsed runtime count across resumes. A pending action after interruption has an unknown outcome: the engine asks for explicit acknowledgment and current-workspace inspection before continuing. Exactly-once execution across a filesystem and SQLite is not claimed.

## File edits and recovery

Paths must resolve inside the chosen workspace and outside protected private/state directories. Existing files require a current SHA-256 hash. Exact edits require a unique old span. Python is parsed before mutation. Original bytes and the intended after-hash are journaled before atomic file replacement.

Undo first checks every current file against the recorded after-hash. Conflicting user edits stop the restore before any file is changed. Restoration covers file-tool operations only; arbitrary subprocess actions are not reversible. A filesystem failure during a multi-file restore can leave a partial restore; backups remain in SQLite for manual recovery.

## Process and model boundaries

Subprocesses receive an argument list, a workspace-contained working directory, a timeout, and bounded output. They run with the user's privileges. These checks are not an OS sandbox. pytest execution uses the active Python interpreter and validates both exit code and parsed JUnit results; zero passing tests, collection errors, failures, and missing/malformed reports are failures.

Ollama schema output and OpenAI-compatible JSON-object output share local validation. The model never has direct filesystem access; calls pass through the registry. Workspace text and memories are marked as untrusted prompt context. This reduces accidental instruction mixing but does not guarantee immunity to prompt injection.

## Scope

This runtime is designed for local Python project tasks. The 1.0 scope does not include a browser agent, MCP client, cloud deployment agent, autonomous Git publishing, multi-agent delegation, fine-tuning, or a semantic memory service. Completed task summaries are searched with lexical overlap. Models, project scale, latency and autonomous success rates must be evaluated separately from the deterministic demo.

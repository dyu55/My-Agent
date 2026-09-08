# Screenshots

Captured in Chromium through actual application interactions on 2026-09-08. Desktop viewport: 1440 × 1050. Mobile viewport: 390 × 844. Full-page images retain their natural height.

RAG uses the bundled fictional Atlas corpus in offline extractive mode. MyAgent uses a labelled deterministic model replay with real file operations, pytest execution, and persisted run state. These images do not demonstrate live model performance.

## MyAgent — Plan, execute and verify

![MyAgent — Plan, execute and verify](screenshots/myagent-overview.png)

A completed task with three dependency-ordered steps, two file changes, and ten passing tests.

## MyAgent — Inspect every edit

![MyAgent — Inspect every edit](screenshots/myagent-diff.png)

Review the actual code changes recorded by the file journal.

## MyAgent — Execution history

![MyAgent — Execution history](screenshots/myagent-events.png)

An ordered record of tool calls, results, reflection outcomes and task completion.

## MyAgent — Mobile run inspector

![MyAgent — Mobile run inspector](screenshots/myagent-mobile.png)

Review a persisted run and its verification results on a narrow screen.

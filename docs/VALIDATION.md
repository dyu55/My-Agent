# Validation record

Validated on macOS, Python 3.12.13, 2026-09-08.

- Automated suite: **47 passed**, no skipped tests.
- Package statement coverage: **88.41%**; CI minimum is 85%.
- Ruff lint and formatting checks passed.
- Source distribution and wheel built; wheel installed in a fresh environment outside the repository.
- Installed CLI and packaged browser assets were exercised successfully.
- Chromium desktop and 390-pixel mobile workflows were inspected. No horizontal overflow was detected. Final browser console: zero errors and zero warnings.
- GitHub CI runs the test suite, packaging and installed-wheel smoke checks on Python 3.11, 3.12 and 3.13, plus a Docker build/execution job. Run results are available under the repository's Actions tab.

The end-to-end demo created temperatures.py and test_temperatures.py, ran ten tests successfully, persisted three completed steps, and produced inspectable diffs and events. Automated tests exercise permission pauses/resume, interrupted actions, call budgets, invalid plans, completion rejection after failed tools, missing verification, stale file hashes, symlink escapes, rollback conflicts, command failures/timeouts, and missing/empty/failing test suites.

Live Ollama was not running and no paid model endpoint was called. Model HTTP protocols were tested with deterministic in-process transports. Live model task success, semantic embedding quality, cost and latency remain unmeasured. Docker was not running locally; the repository CI container job supplies that validation. Two upstream TestClient deprecation warnings occur in the Python test suite and do not affect the application browser console.

## UI redesign verification — 2026-09-08

The redesigned interface was checked in Chromium at 1440 × 1050 and 390 × 844. The current checkout test suite passed (47 tests), as did Ruff and JavaScript syntax checks. Source screenshots were captured from the running application, including the mobile layout. See `SCREENSHOTS.md` and `DESIGN.md` for the new interface and capture context.

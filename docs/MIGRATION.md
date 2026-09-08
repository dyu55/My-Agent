# Migration from the earlier MyAgent

Version 1.0 is a new package under `src/myagent/`, with a new CLI and run database. The former `main.py`, top-level `agent`, `utils`, `memory`, `skills`, and `wiki` imports are not compatibility APIs.

1. Create a fresh Python 3.11+ virtual environment and install the new package.
2. Choose the project directory with `--workspace`. New state is stored in that directory's `.myagent/` folder.
3. Configure `MYAGENT_PROVIDER`, `MYAGENT_MODEL`, `MYAGENT_BASE_URL`, and optionally `MYAGENT_API_KEY`, or pass their CLI equivalents.
4. Start a new run. Legacy checkpoints, memory databases and cached model outputs are preserved as archives but are not automatically imported or replayed.
5. Inspect the run with `myagent show`, `myagent runs`, or `myagent serve`.

The previous source is retained by tag `before-greenfield-v1-20260908`. A separate Git worktree at that tag can run the previous version without modifying the new source. Existing secrets and generated projects are not included in the new package or published with the rewrite.

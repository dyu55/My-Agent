# Comprehensive Coding Agent Test Suite

## Test Overview

This test suite evaluates Qwen3.6:27b and Gemma4:31b coding capabilities across 8 different tasks.

### Test Tasks

| Round | Task | Description | Estimated Time |
|-------|------|-------------|-----------------|
| 1 | CLI CRUD | Contact management CLI with JSON storage | ~40 min |
| 2 | Algorithm | Binary search, merge sort, BFS | ~35 min |
| 3 | Bug Fixing | Fix calculator bugs with tests | ~30 min |
| 4 | Web API | Flask REST API for task manager | ~45 min |
| 5 | Data Processing | CSV processing with pandas | ~35 min |
| 6 | TDD | Password validator with TDD | ~50 min |
| 7 | Refactoring | Refactor messy code | ~40 min |
| 8 | Full-Stack | Simple blog system | ~50 min |

**Total estimated time: ~5-6 hours**

## How to Run

### Option 1: Simple Run (Before Sleep)
```bash
cd /Users/donglingyu/Documents/MyAgent/test_workspace/comprehensive_test
./run_tests.sh
```

### Option 2: Run with nohup (Recommended for overnight)
```bash
cd /Users/donglingyu/Documents/MyAgent/test_workspace/comprehensive_test
nohup ./run_tests.sh > test_output.log 2>&1 &
echo "Test started in background. PID: $!"
```

### Option 3: Run with tee (see output in real-time)
```bash
cd /Users/donglingyu/Documents/MyAgent/test_workspace/comprehensive_test
./run_tests.sh 2>&1 | tee test_log.txt
```

## Check Status

### During test:
```bash
# Check current progress
cat /Users/donglingyu/Documents/MyAgent/test_workspace/comprehensive_test/test_log.txt

# Check if still running
ps aux | grep run_tests.sh | grep -v grep
```

### After test:
```bash
# View summary
cat /Users/donglingyu/Documents/MyAgent/test_workspace/comprehensive_test/results/summary.json

# View detailed report
cat /Users/donglingyu/Documents/MyAgent/test_workspace/comprehensive_test/results/report.md
```

## Output Structure

```
comprehensive_test/
├── round1-qwen3.6:27b-q4_K_M/
│   ├── response.json       # Raw API response
│   ├── metadata.txt         # Test metadata
│   └── project/             # Generated code
├── round1-gemma4:31b/
│   ├── response.json
│   ├── metadata.txt
│   └── project/
├── round2-qwen3.6:27b-q4_K_M/
│   └── ...
├── ...
├── test_log.txt            # Execution log
└── results/
    ├── summary.json        # Machine-readable summary
    └── report.md           # Human-readable report
```

## Notes

- All prompts are in **English** only
- Each task tests different coding skills
- Tests will run continuously until all 8 rounds complete
- If Ollama server is unavailable, the test will fail for that task
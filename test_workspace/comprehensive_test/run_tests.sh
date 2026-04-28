#!/bin/bash
# Comprehensive Coding Agent Test Suite
# Tests Qwen3.6:27b vs Gemma4:31b on multiple coding tasks
# Estimated runtime: ~7 hours

BASE_DIR="/Users/donglingyu/Documents/MyAgent/test_workspace/comprehensive_test"
OLLAMA_HOST="http://192.168.0.124:11434"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "[$(date '+%H:%M:%S')] $1" | tee -a "$BASE_DIR/test_log.txt"
}

log_header() {
    log "=============================================================="
    log "$1"
    log "=============================================================="
}

# Test projects with detailed English prompts
declare -a PROJECTS=(
    "cli_crud:CLI CRUD Application:Create a CLI tool for managing contacts with argparse subcommands: add, list, update, delete. Store data in JSON file at ~/.contacts.json. Fields: name, email, phone. Include search functionality. Python 3.10+, type hints, pytest with 5+ tests. Project structure: src/main.py, src/models.py, src/storage.py, src/commands/, tests/. Output format: ===FILE: path ==="

    "algorithm:Algorithm Implementation:Implement a Python module with: 1) Binary search with tests, 2) Merge sort with tests, 3) BFS graph traversal with tests. Include time complexity analysis in comments. Python 3.10+, type hints, pytest with 10+ tests covering edge cases. Structure: algorithms/binary_search.py, algorithms/merge_sort.py, algorithms/graph.py, tests/test_algorithms.py. ===FILE: path ==="

    "bug_fixing:Bug Fixing Challenge:Fix the bugs in this Python code. The code is a calculator that has several bugs: def calculate(expr): result = eval(expr); return result (no error handling, eval is unsafe). def divide(a, b): return a/b (no zero division check). def factorial(n): if n==0: return 1; else: return n*factorial(n) (no negative number check). Create fixed versions with proper error handling, input validation, and pytest tests. Structure: calculator/calculator.py, calculator/exceptions.py, tests/test_calculator.py. ===FILE: path ==="

    "web_api:Web API Development:Create a Flask REST API for a task manager. Endpoints: GET /tasks (list all), POST /tasks (create), GET /tasks/<id> (get one), PUT /tasks/<id> (update), DELETE /tasks/<id> (delete). Use SQLite for storage. Include request validation, error handling, and OpenAPI documentation. Python 3.10+, Flask, pytest with 8+ integration tests. Structure: app.py, models.py, routes.py, schemas.py, tests/test_api.py, requirements.txt. ===FILE: path ==="

    "data_processing:Data Processing Script:Create a Python script that processes CSV files. Features: 1) Read CSV with pandas, 2) Filter rows by conditions, 3) Aggregate data (sum, average, count), 4) Export to new CSV/JSON. Support command line arguments for input file, output format, and filter criteria. Include progress bar using tqdm. Python 3.10+, pandas, type hints, pytest with 6+ tests. Structure: data_processor/main.py, data_processor/processor.py, data_processor/cli.py, tests/test_processor.py. ===FILE: path ==="

    "tdd_password:Test-Driven Development:Implement a password validator using TDD. First write tests, then implement: Requirements: 1) Minimum 8 characters, 2) At least one uppercase, 3) At least one lowercase, 4) At least one digit, 5) At least one special character. Return detailed error messages for each failed rule. Python 3.10+, pytest, follow red-green-refactor cycle. Structure: validator/password.py, validator/rules.py, tests/test_password.py. ===FILE: path ==="

    "refactoring:Code Refactoring:Refactor this messy Python code into clean, maintainable code. Original code has: global variables, 200+ line functions, duplicate code, no type hints, poor naming. Create: clean class structure, small functions (<30 lines), proper encapsulation, type hints, docstrings. Original messy code will be provided inline. Run original tests to ensure functionality preserved. Python 3.10+, pytest. Structure: refactored/user_service.py, refactored/validators.py, refactored/database.py, tests/test_user_service.py. ===FILE: path ==="

    "full_stack:Full-Stack Project:Create a simple blog system with: 1) Flask web server with Jinja2 templates, 2) SQLite database for posts and users, 3) REST API for posts, 4) Basic authentication (login/logout/register), 5) CRUD for blog posts. Include proper folder structure, error handling, and basic styling. Python 3.10+, Flask, pytest with 10+ tests. Structure: app.py, models.py, routes/auth.py, routes/posts.py, templates/, static/, tests/test_blog.py, requirements.txt. ===FILE: path ==="
)

# Run tests
round_num=0
for project in "${PROJECTS[@]}"; do
    IFS=';' read -r project_name prompt <<< "$project"
    round_num=$((round_num + 1))

    log_header "ROUND $round_num: $project_name"

    for model in "qwen3.6:27b-q4_K_M" "gemma4:31b"; do
        model_name=$(echo $model | cut -d':' -f1)
        log_header "Testing $model on: $project_name"

        output_dir="$BASE_DIR/round${round_num}-${model_name}"
        mkdir -p "$output_dir"

        start_time=$(date +%s)

        # Call Ollama API
        curl -s -X POST "$OLLAMA_HOST/api/generate" \
            -H "Content-Type: application/json" \
            -d "{\"model\":\"$model\",\"prompt\":$(echo "$prompt" | jq -Rs .),\"stream\":false}" \
            > "$output_dir/response.json" 2>&1

        end_time=$(date +%s)
        duration=$((end_time - start_time))

        # Check if response is valid JSON
        if jq -e . "$output_dir/response.json" > /dev/null 2>&1; then
            eval_count=$(jq -r '.eval_count // 0' "$output_dir/response.json")
            response_len=$(jq -r '.response | length' "$output_dir/response.json")

            log "$model | Duration: ${duration}s | Tokens: $eval_count | Chars: ${response_len}"

            # Parse and create files using Python
            python3 << PYEOF
import json
import re
import os
import subprocess

output_dir = "$output_dir"
snippet_dir = f"{output_dir}/project"
os.makedirs(snippet_dir, exist_ok=True)

try:
    with open(f"{output_dir}/response.json", 'r') as f:
        data = json.load(f)

    response = data.get('response', '')

    # Parse files - look for ===FILE: markers
    pattern = r'===FILE:\s*([^\s]+)\s*===\n?(.*?)(?====FILE:|$)'
    matches = re.findall(pattern, response, re.DOTALL)

    files_created = []
    for filename, content in matches:
        content = content.strip()
        # Remove markdown code blocks
        if content.startswith('```python'):
            content = content[9:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]

        if len(content) < 20:
            continue

        if filename and (filename.endswith('.py') or filename.endswith('.toml') or filename.endswith('.md') or filename.endswith('.txt') or '.html' in filename or '.css' in filename):
            filepath = f"{snippet_dir}/{filename}"
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(content.strip())
            files_created.append(filename)

    print(f"Created {len(files_created)} files: {', '.join(files_created[:5])}{'...' if len(files_created) > 5 else ''}")

    # Test the code
    os.chdir(snippet_dir)

    # Find main entry point
    main_files = []
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f in ['main.py', 'app.py', 'calculator.py', 'validator.py', 'data_processor.py', 'user_service.py', 'algorithms.py']:
                main_files.append(os.path.join(root, f))

    runnable = "no"
    tests_passed = "0"
    tests_failed = "0"

    if main_files:
        main_file = main_files[0]

        # Try running the code
        try:
            result = subprocess.run(['python3', main_file, '--help'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 or 'usage' in result.stdout.lower() or 'help' in result.stdout.lower():
                runnable = "yes"
                print(f"  ✓ CLI runs: {main_file}")
            else:
                # Try as module
                result = subprocess.run(['python3', '-c', 'import sys; sys.path.insert(0, "."); exec(open(".").read())'],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    runnable = "yes"
                    print(f"  ✓ Code executes")
        except:
            pass

    # Run pytest
    try:
        result = subprocess.run(['python3', '-m', 'pytest', '.', '-v', '--tb=short', '-x'],
                              capture_output=True, text=True, timeout=60, cwd=snippet_dir)
        passed = re.search(r'(\d+) passed', result.stdout)
        failed = re.search(r'(\d+) failed', result.stdout)
        tests_passed = passed.group(1) if passed else "0"
        tests_failed = failed.group(1) if failed else "0"
        print(f"  ✓ Tests: {tests_passed} passed, {tests_failed} failed")
    except Exception as e:
        print(f"  ✗ Tests error: {str(e)[:50]}")

    # Write metadata
    with open(f"{output_dir}/metadata.txt", 'w') as f:
        f.write(f"model={model}\n")
        f.write(f"project={project_name}\n")
        f.write(f"duration={duration}\n")
        f.write(f"tokens={eval_count}\n")
        f.write(f"files={len(files_created)}\n")
        f.write(f"runnable={runnable}\n")
        f.write(f"tests_passed={tests_passed}\n")
        f.write(f"tests_failed={tests_failed}\n")
        f.write(f"timestamp={TIMESTAMP}\n")

except Exception as e:
    print(f"Error: {e}")
    with open(f"{output_dir}/error.txt", 'w') as f:
        f.write(str(e))
PYEOF
        else
            log "  ✗ API call failed"
            echo "api_failed=yes" >> "$output_dir/metadata.txt"
        fi

        # Small delay between models
        sleep 5
    done

    log "Round $round_num completed"
    sleep 30
done

# Generate summary report
log_header "ALL TESTS COMPLETED"

python3 << 'SUMMARY_EOF'
import json
import os
from datetime import datetime

base_dir = "/Users/donglingyu/Documents/MyAgent/test_workspace/comprehensive_test"
results = []

for item in sorted(os.listdir(base_dir)):
    if item.startswith('round') and '-' in item:
        parts = item.split('-')
        round_num = parts[0].replace('round', '')
        model = '-'.join(parts[1:])

        metadata_file = f"{base_dir}/{item}/metadata.txt"
        if os.path.exists(metadata_file):
            metadata = {}
            with open(metadata_file, 'r') as f:
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        metadata[k] = v

            results.append({
                'round': int(round_num),
                'model': model,
                'project': metadata.get('project', 'unknown'),
                'duration': int(metadata.get('duration', 0)),
                'tokens': int(metadata.get('tokens', 0)),
                'files': int(metadata.get('files', 0)),
                'runnable': metadata.get('runnable', 'no'),
                'tests_passed': int(metadata.get('tests_passed', 0)),
                'tests_failed': int(metadata.get('tests_failed', 0)),
            })

# Sort by round
results.sort(key=lambda x: (x['round'], x['model']))

# Write JSON summary
os.makedirs(f"{base_dir}/results", exist_ok=True)
with open(f"{base_dir}/results/summary.json", 'w') as f:
    json.dump(results, f, indent=2)

# Generate markdown report
report = f"""# Comprehensive Coding Agent Test Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary Statistics

### By Model
"""

# Calculate statistics
qwen_results = [r for r in results if r['model'] == 'qwen3.6:27b-q4_K_M']
gemma_results = [r for r in results if r['model'] == 'gemma4:31b']

for model_name, model_results in [("Qwen 3.6:27b", qwen_results), ("Gemma 4:31b", gemma_results)]:
    if model_results:
        total_time = sum(r['duration'] for r in model_results)
        total_tokens = sum(r['tokens'] for r in model_results)
        total_files = sum(r['files'] for r in model_results)
        runnable_count = sum(1 for r in model_results if r['runnable'] == 'yes')
        total_tests = sum(r['tests_passed'] for r in model_results)

        report += f"""
#### {model_name}
- Total rounds: {len(model_results)}
- Total time: {total_time//60} min ({total_time}s)
- Average time per task: {total_time//len(model_results)//60} min
- Total tokens generated: {total_tokens:,}
- Total files created: {total_files}
- Runnable code: {runnable_count}/{len(model_results)}
- Total tests passed: {total_tests}
"""

report += """
## Detailed Results

| Round | Model | Project | Duration | Tokens | Files | Runnable | Tests |
|-------|-------|---------|----------|--------|-------|----------|-------|
"""

for r in results:
    status = "✓" if r['runnable'] == 'yes' else "✗"
    report += f"| {r['round']} | {r['model']} | {r['project']} | {r['duration']//60}m | {r['tokens']} | {r['files']} | {status} | {r['tests_passed']}/{r['tests_passed']+r['tests_failed']} |\n"

report += """
## Conclusion

"""

# Winner analysis
if qwen_results and gemma_results:
    qwen_runnable = sum(1 for r in qwen_results if r['runnable'] == 'yes')
    gemma_runnable = sum(1 for r in gemma_results if r['runnable'] == 'yes')
    qwen_tests = sum(r['tests_passed'] for r in qwen_results)
    gemma_tests = sum(r['tests_passed'] for r in gemma_results)
    qwen_avg_tokens = sum(r['tokens'] for r in qwen_results) // len(qwen_results)
    gemma_avg_tokens = sum(r['tokens'] for r in gemma_results) // len(gemma_results)

    report += f"""### Speed
- Qwen average: {qwen_avg_tokens:,} tokens/task
- Gemma average: {gemma_avg_tokens:,} tokens/task
- Speed ratio: ~{qwen_avg_tokens//gemma_avg_tokens}x (Qwen generates more content)

### Code Quality
- Qwen runnable: {qwen_runnable}/{len(qwen_results)} ({qwen_runnable*100//len(qwen_results)}%)
- Gemma runnable: {gemma_runnable}/{len(gemma_results)} ({gemma_runnable*100//len(gemma_results)}%)

### Test Coverage
- Qwen tests: {qwen_tests} total
- Gemma tests: {gemma_tests} total
"""

with open(f"{base_dir}/results/report.md", 'w') as f:
    f.write(report)

print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
for r in results:
    status = "✓" if r['runnable'] == 'yes' else "✗"
    print(f"Round {r['round']:2} | {r['model']:20} | {r['project']:25} | {status} | {r['tests_passed']} tests")

print("="*60)
print(f"\nResults saved to: {base_dir}/results/")
print(f"  - summary.json (raw data)")
print(f"  - report.md (markdown report)")
SUMMARY_EOF

log "All tests completed! Results saved to $BASE_DIR/results/"

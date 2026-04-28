#!/bin/bash
# Overnight Coding Agent Test Suite
# Tests Qwen3.6:27b vs Gemma4:31b on multiple projects

BASE_DIR="/Users/donglingyu/Documents/MyAgent/test_workspace/night_tests"
OLLAMA_HOST="http://192.168.0.124:11434"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

log() {
    echo "[$(date '+%H:%M:%S')] $1" | tee -a "$BASE_DIR/test_log.txt"
}

test_model() {
    local model=$1
    local project_name=$2
    local prompt=$3
    local output_dir=$4

    log "=========================================="
    log "Testing $model on: $project_name"
    log "=========================================="

    local start_time=$(date +%s)
    local response_file="$output_dir/response.json"

    # Create output directory
    mkdir -p "$output_dir"

    # Call Ollama API
    curl -s -X POST "$OLLAMA_HOST/api/generate" \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$model\",\"prompt\":$(echo "$prompt" | jq -Rs .),\"stream\":false}" \
        > "$response_file" 2>&1

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Check if response is valid JSON
    if jq -e . "$response_file" > /dev/null 2>&1; then
        local response_length=$(jq -r '.response | length' "$response_file")
        local eval_count=$(jq -r '.eval_count // 0' "$response_file")
        local total_duration=$(jq -r '.total_duration // 0' "$response_file")

        log "$model | $project_name | Duration: ${duration}s | Tokens: $eval_count | Response: ${response_length}chars"

        # Parse and create files
        python3 << PYEOF
import json
import re
import os

output_dir = "$output_dir"
snippet_dir = f"{output_dir}/snippets"
os.makedirs(snippet_dir, exist_ok=True)

try:
    with open(f"{output_dir}/response.json", 'r') as f:
        data = json.load(f)

    response = data.get('response', '')
    pattern = r'===FILE:\s*([^\s]+)\s*===\n(.*?)(?====FILE:|$)'
    matches = re.findall(pattern, response, re.DOTALL)

    files_created = []
    for filename, content in matches:
        content = content.strip()
        if content.startswith('```python'):
            content = content[9:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]

        if len(content) < 10:
            continue

        if filename and (filename.endswith('.py') or filename.endswith('.toml') or filename.endswith('.md')):
            filepath = f"{snippet_dir}/{filename}"
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(content.strip())
            files_created.append(filename)

    print(f"Created {len(files_created)} files")
except Exception as e:
    print(f"Error: {e}")
PYEOF

        # Test the generated code
        cd "$output_dir/snippets"

        # Try running main.py
        local test_result=$(python3 -m src.main --help 2>&1 | head -1)
        if [[ "$test_result" == *"usage"* ]] || [[ "$test_result" == *"add"* ]]; then
            log "  ✓ CLI runs successfully"
            echo "runnable=yes" >> "$output_dir/metadata.txt"
        else
            log "  ✗ CLI failed to run"
            echo "runnable=no" >> "$output_dir/metadata.txt"
        fi

        # Run pytest
        local pytest_result=$(python3 -m pytest tests/ -v 2>&1 | tail -5)
        local passed=$(echo "$pytest_result" | grep -oE "[0-9]+ passed" | cut -d' ' -f1)
        local failed=$(echo "$pytest_result" | grep -oE "[0-9]+ failed" | cut -d' ' -f1)
        log "  Tests: $passed passed, $failed failed"
        echo "tests_passed=$passed" >> "$output_dir/metadata.txt"
        echo "tests_failed=$failed" >> "$output_dir/metadata.txt"

    else
        log "  ✗ API call failed or returned invalid JSON"
        echo "api_failed=yes" >> "$output_dir/metadata.txt"
        cat "$response_file" >> "$BASE_DIR/errors.txt"
    fi

    echo "$model=$model" >> "$output_dir/metadata.txt"
    echo "project=$project_name" >> "$output_dir/metadata.txt"
    echo "duration=${duration}" >> "$output_dir/metadata.txt"
    echo "timestamp=$TIMESTAMP" >> "$output_dir/metadata.txt"
}

# Test Projects
PROJECTS=(
    "cli_todo:CLI待办事项管理器 - argparse子命令add/list/done/delete，JSON文件存储~/.todos.json，优先级和截止日期"
    "cli_snippets:CLI代码片段管理器 - argparse子命令add/list/get/edit/delete/search，SQLite数据库~/.snippets.db"
    "file_searcher:文件搜索工具 - 支持正则表达式搜索，递归目录遍历，多种过滤选项"
    "http_server:简单HTTP服务器 - 处理GET/POST请求，静态文件服务，路由系统"
    "markdown_blog:Markdown博客生成器 - 解析Markdown，生成HTML，模板系统，分类和标签"
)

# Run tests for each project
for i in "${!PROJECTS[@]}"; do
    project="${PROJECTS[$i]}"
    IFS=':' read -r project_name prompt <<< "$project"

    log ""
    log "=========================================="
    log "ROUND $((i+1)): $project_name"
    log "=========================================="

    # Test Qwen
    test_model "qwen3.6:27b-q4_K_M" "$project_name" \
        "请用Python生成一个$prompt。要求：Python 3.10+，argparse标准库，类型提示，pytest测试，合理的项目结构。输出格式：每个文件用 ===FILE: 路径 === 分隔，只输出代码。" \
        "$BASE_DIR/round$((i+1))/qwen"

    # Small delay between models
    sleep 10

    # Test Gemma
    test_model "gemma4:31b" "$project_name" \
        "请用Python生成一个$prompt。要求：Python 3.10+，argparse标准库，类型提示，pytest测试，合理的项目结构。输出格式：每个文件用 ===FILE: 路径 === 分隔，只输出代码。" \
        "$BASE_DIR/round$((i+1))/gemma"

    log "Round $((i+1)) completed"
    sleep 30
done

# Generate summary report
log ""
log "=========================================="
log "ALL TESTS COMPLETED"
log "=========================================="

python3 << 'PYEOF'
import os
import json

base_dir = "/Users/donglingyu/Documents/MyAgent/test_workspace/night_tests"
results = []

for round_dir in sorted(os.listdir(base_dir)):
    if not round_dir.startswith('round'):
        continue

    for model in ['qwen', 'gemma']:
        model_dir = f"{base_dir}/{round_dir}/{model}"
        metadata_file = f"{model_dir}/metadata.txt"

        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                metadata = dict(line.strip().split('=', 1) for line in f if '=' in line)

            results.append({
                'round': round_dir,
                'model': model,
                'project': metadata.get('project', 'unknown'),
                'runnable': metadata.get('runnable', 'unknown'),
                'tests_passed': metadata.get('tests_passed', '0'),
                'tests_failed': metadata.get('tests_failed', '0'),
                'duration': metadata.get('duration', '0'),
            })

# Write results
with open(f"{base_dir}/results/summary.json", 'w') as f:
    json.dump(results, f, indent=2)

print("\n=== SUMMARY ===")
for r in results:
    status = "✓" if r['runnable'] == 'yes' else "✗"
    print(f"{r['round']} | {r['model']:8} | {r['project']:20} | {status} | Tests: {r['tests_passed']}/{int(r['tests_passed'])+int(r['tests_failed'])} | {r['duration']}s")

print(f"\nTotal rounds: {len(results)}")
print(f"Results saved to: {base_dir}/results/summary.json")
PYEOF

log "Test suite completed. Results saved to $BASE_DIR/results/"

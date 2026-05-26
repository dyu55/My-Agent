#!/bin/bash
# Overnight Test Runner - Runs all tests sequentially
# Usage: ./run_overnight_tests.sh

set -e

LOG_DIR="tests"
BASE_URL="http://192.168.0.124:11434"

echo "=============================================="
echo "  OVERNIGHT MODEL TEST RUNNER"
echo "  Started at: $(date)"
echo "=============================================="

# Test 1: qwen3.6:27b-q4_K_M
if [ ! -f "$LOG_DIR/results_qwen36.json" ]; then
    echo ""
    echo "=============================================="
    echo "  TEST 1: qwen3.6:27b-q4_K_M"
    echo "  Started at: $(date)"
    echo "=============================================="
    python3 -u "$LOG_DIR/model_comparison_test.py" \
        --model qwen3.6:27b-q4_K_M \
        --output "$LOG_DIR/results_qwen36.json" \
        --base-url "$BASE_URL" \
        --timeout 600 \
        2>&1 | tee "$LOG_DIR/test_1_qwen36.log"
    echo "Test 1 completed at: $(date)"
else
    echo "Test 1 already completed, skipping..."
fi

# Test 2: gemma4:31b
if [ ! -f "$LOG_DIR/results_gemma4.json" ]; then
    echo ""
    echo "=============================================="
    echo "  TEST 2: gemma4:31b"
    echo "  Started at: $(date)"
    echo "=============================================="
    python3 -u "$LOG_DIR/model_comparison_test.py" \
        --model gemma4:31b \
        --output "$LOG_DIR/results_gemma4.json" \
        --base-url "$BASE_URL" \
        --timeout 600 \
        2>&1 | tee "$LOG_DIR/test_2_gemma4.log"
    echo "Test 2 completed at: $(date)"
else
    echo "Test 2 already completed, skipping..."
fi

# Test 3: Claude Opus
if [ ! -f "$LOG_DIR/results_claude_opus.json" ]; then
    echo ""
    echo "=============================================="
    echo "  TEST 3: Claude Opus"
    echo "  Started at: $(date)"
    echo "=============================================="
    python3 -u "$LOG_DIR/claude_opus_test.py" \
        --output "$LOG_DIR/results_claude_opus.json" \
        2>&1 | tee "$LOG_DIR/test_3_claude.log"
    echo "Test 3 completed at: $(date)"
else
    echo "Test 3 already completed, skipping..."
fi

echo ""
echo "=============================================="
echo "  ALL TESTS COMPLETED"
echo "  Finished at: $(date)"
echo "=============================================="

# Generate HTML report
echo ""
echo "Generating HTML report..."
python3 -u "$LOG_DIR/generate_report.py"

echo ""
echo "Done! Report generated at: tests/model_comparison_report.html"
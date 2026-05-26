#!/bin/bash
# Test script for 8-hour overnight test plan
# Usage: ./run_tests.sh [model_name]

set -e

# Default to localhost
export OLLAMA_HOST=${OLLAMA_HOST:-http://localhost:11434}

MODEL=${1:-qwen3.5:9b}
echo "========================================"
echo "Testing Model: $MODEL"
echo "Server: $OLLAMA_HOST"
echo "========================================"
echo ""

# Verify connection
echo "Verifying connection..."
curl -s "$OLLAMA_HOST/api/tags" | python3 -c "import sys,json; d=json.load(sys.stdin); print('Available models:', [m['name'] for m in d['models']])"
echo ""

# Phase 1: Basic Functionality
echo "========================================"
echo "Phase 1: Basic Functionality Test"
echo "========================================"

echo ""
echo "Test 1: Code Generation"
python3 main.py "Create a simple calculator that can add, subtract, multiply, divide" --model $MODEL

echo ""
echo "Test 2: Task Planning"
python3 main.py "Plan a REST API with 5 endpoints for a blog" --model $MODEL

echo ""
echo "Test 3: File Operations"
python3 main.py "Create a hello.py file that prints 'Hello World'" --model $MODEL

echo ""
echo "========================================"
echo "Phase 1 Complete!"
echo "========================================"

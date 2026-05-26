#!/usr/bin/env python3
"""Ollama Cloud model comparison test — 3 models x 15 tasks."""

import os
import sys
import time
import json
from datetime import datetime

os.chdir('/Users/donglingyu/Documents/MyAgent')
from dotenv import load_dotenv
load_dotenv()

from utils.model_provider import ModelManager

# Test tasks (same as test_models.py)
test_tasks = [
    ('Simple-1', 'Write a hello world function in Python'),
    ('Simple-2', 'Calculate the sum of 1 to 100'),
    ('Simple-3', 'Reverse the string "hello world"'),
    ('Simple-4', 'Check if 123 is prime'),
    ('Simple-5', 'Convert JSON string to dict: {"name": "test", "age": 25}'),
    ('Medium-1', 'Implement a binary search tree with insert and search methods'),
    ('Medium-2', 'Write a decorator that measures function execution time'),
    ('Medium-3', 'Create a simple HTTP GET request handler using requests library'),
    ('Medium-4', 'Implement a thread-safe singleton pattern in Python'),
    ('Medium-5', 'Write a function to deep merge two dictionaries'),
    ('Complex-1', 'Build a rate limiter that supports sliding window algorithm'),
    ('Complex-2', 'Implement a LRU cache with O(1) get and put operations'),
    ('Complex-3', 'Write a parser for simple expressions: +,-,*,/ and parentheses'),
    ('Edge-1', 'Write a function that extracts all values by key "id" from deeply nested dict'),
    ('Edge-2', 'Implement safe JSON parser that prevents prototype pollution attacks'),
]

models = [
    ('gemma4:31b', 'gemma4-31b', '62GB, Google'),
    ('nemotron-3-nano:30b', 'nemotron-nano', '32GB, NVIDIA'),
    ('qwen3-coder-next', 'qwen3-coder', '81GB, Alibaba 代码专用'),
]

results = {}
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

def log(msg):
    print(msg)
    sys.stdout.flush()

def run_single_test(manager, task_name, prompt):
    """Run a single test with retry."""
    for attempt in range(3):
        try:
            start = time.time()
            response = manager.chat(
                f"{prompt}\n\nProvide working Python code.",
                timeout=180,
            )
            elapsed = time.time() - start

            has_code = '```python' in response or 'def ' in response or 'class ' in response

            return {
                'success': True,
                'task': task_name,
                'response': response,
                'elapsed': round(elapsed, 2),
                'attempts': attempt + 1,
                'has_code': has_code,
                'length': len(response),
            }
        except Exception as e:
            err = str(e)
            log(f"  Attempt {attempt+1} error: {err[:200]}")
            if '429' in err or 'RESOURCE_EXHAUSTED' in err or 'rate' in err.lower():
                log("  Waiting 65s for rate limit...")
                time.sleep(65)
            else:
                time.sleep(10)
    return {
        'success': False,
        'task': task_name,
        'error': 'Failed after 3 attempts',
    }

def main():
    log('=' * 70)
    log('OLLAMA CLOUD MODEL COMPARISON — 15 Tasks x 3 Models')
    log('=' * 70)
    log(f'Models: gemma4:31b | nemotron-3-nano:30b | qwen3-coder-next\n')

    total = len(test_tasks) * len(models)
    current = 0
    model_results = {mid: {} for _, mid, _ in models}

    for model_name, model_id, model_desc in models:
        log(f'\n{"="*50}')
        log(f'MODEL: {model_name}  ({model_desc})')
        log(f'{"="*50}')

        manager = ModelManager()
        manager.set_model('ollama', model_name)
        log(f'Health: {manager.health_check()}\n')

        for task_id, task_name in test_tasks:
            current += 1
            log(f'[{current}/{total}] {task_id} — {task_name[:60]}')

            result = run_single_test(manager, task_name, task_name)
            model_results[model_id][task_id] = result

            if result['success']:
                log(f"  ✅ {result['elapsed']}s | {result['length']} chars | code:{result['has_code']}")
            else:
                log(f"  ❌ {result.get('error', 'unknown')[:100]}")

            # Save progress after each test
            with open(f'logs/ollama_progress_{timestamp}.json', 'w') as f:
                json.dump(model_results, f, indent=2, ensure_ascii=False)

            time.sleep(5)  # gentle on the API

        # Extra sleep between models
        if model_id != models[-1][1]:
            log('\n  Waiting 30s before next model...')
            time.sleep(30)

    # Summary
    log('\n' + '=' * 70)
    log('SUMMARY')
    log('=' * 70)

    for _, model_id, model_desc in models:
        res = model_results.get(model_id, {})
        successes = [r for r in res.values() if r['success']]
        log(f'\n{model_id} ({model_desc}):')
        log(f"  ✅ {len(successes)}/{len(res)} passed")
        if successes:
            avg_time = sum(r['elapsed'] for r in successes) / len(successes)
            avg_len = sum(r['length'] for r in successes) / len(successes)
            code_count = sum(1 for r in successes if r['has_code'])
            log(f"  ⏱  Avg time: {avg_time:.1f}s")
            log(f"  📏 Avg length: {avg_len:.0f} chars")
            log(f"  💻 Code responses: {code_count}/{len(successes)}")

    log(f'\nProgress saved to: logs/ollama_progress_{timestamp}.json')

if __name__ == '__main__':
    main()

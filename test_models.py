#!/usr/bin/env python3
"""Simplified model comparison test - runs one test at a time with immediate output."""

import os
import sys
import time
import json
from datetime import datetime

os.chdir('/Users/donglingyu/Documents/MyAgent')
from dotenv import load_dotenv
load_dotenv()

from utils.model_provider import ModelManager

# Test tasks
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
    ('gemma-4-26b-a4b-it', '26b'),
    ('gemma-4-31b-it', '31b'),
    ('gemini-2.5-flash', '2.5-flash'),
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
            response = manager.chat(f"{prompt}\n\nProvide working Python code.", timeout=180)
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
            log(f"  Attempt {attempt+1} error: {err[:150]}")
            if '429' in err or 'RESOURCE_EXHAUSTED' in err:
                log("  Waiting 65s for rate limit...")
                time.sleep(65)
            else:
                time.sleep(5)
    return {
        'success': False,
        'task': task_name,
        'error': 'Failed after 3 attempts',
    }

def main():
    log('=' * 70)
    log('MODEL COMPARISON TEST - 15 Tasks x 3 Models')
    log('=' * 70)

    total = len(test_tasks) * len(models)
    current = 0
    model_results = {mid: {} for _, mid in models}

    for model_name, model_id in models:
        log(f'\n{"="*50}')
        log(f'MODEL: {model_name} ({model_id})')
        log(f'{"="*50}')

        manager = ModelManager()
        manager.set_model('gemini', model_name)
        log(f'Health: {manager.health_check()}\n')

        for task_id, task_name in test_tasks:
            current += 1
            log(f'[{current}/{total}] {task_id} - {task_name}')

            result = run_single_test(manager, task_name, task_name)
            model_results[model_id][task_id] = result

            if result['success']:
                log(f"  ✅ {result['elapsed']}s | {result['length']} chars | code:{result['has_code']}")
            else:
                log(f"  ❌ {result.get('error', 'unknown')[:80]}")

            # Save progress after each test
            with open(f'test_progress_{timestamp}.json', 'w') as f:
                json.dump(model_results, f)

            time.sleep(3)

    # Summary
    log('\n' + '=' * 70)
    log('SUMMARY')
    log('=' * 70)

    for model_id, res in model_results.items():
        successes = [r for r in res.values() if r['success']]
        log(f'\n{model_id}:')
        log(f"  ✅ {len(successes)}/{len(res)} passed")
        if successes:
            avg_time = sum(r['elapsed'] for r in successes) / len(successes)
            avg_len = sum(r['length'] for r in successes) / len(successes)
            code_count = sum(1 for r in successes if r['has_code'])
            log(f"  ⏱ Avg time: {avg_time:.1f}s")
            log(f"  📏 Avg length: {avg_len:.0f} chars")
            log(f"  💻 Code responses: {code_count}/{len(successes)}")

    log(f'\nProgress saved to: test_progress_{timestamp}.json')

if __name__ == '__main__':
    main()
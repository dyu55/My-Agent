#!/usr/bin/env python3
"""Laptop cooling stress test — runs local Ollama model continuously."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

MODEL = "qwen3:8b"
OLLAMA_URL = "http://localhost:11434/api/generate"

PROMPTS = [
    "Write a detailed analysis of sorting algorithms, comparing quicksort, mergesort, and heapsort. Include time complexity, space complexity, and real-world performance considerations.",
    "Implement a complete binary search tree in Python with insert, delete, search, and in-order traversal. Include type hints and docstrings.",
    "Explain how CPU caching works, including L1/L2/L3 caches, cache lines, associativity, and how software can be optimized for cache locality.",
    "Write a Python implementation of a LRU cache with O(1) get and put operations. Use a doubly linked list and hash map.",
    "Describe the differences between processes and threads, covering memory layout, context switching overhead, synchronization primitives, and when to use each.",
    "Implement a thread-safe producer-consumer queue in Python using threading primitives. Include proper shutdown signaling.",
    "Explain virtual memory, page tables, TLB, page faults, and how the OS handles memory-mapped files.",
    "Write a Python implementation of a trie (prefix tree) with insert, search, and startsWith methods. Include auto-complete functionality.",
    "Analyze the trade-offs between microservices and monolithic architectures. Cover deployment, scaling, debugging, and team organization.",
    "Implement a simple HTTP server in Python using sockets. Handle GET and POST requests, serve static files, and return proper status codes.",
]


def get_cpu_temp():
    """Try to get CPU temperature on macOS."""
    try:
        out = subprocess.check_output(
            ["sudo", "powermetrics", "--samplers", "smc", "-n", "1", "-i", "1000"],
            timeout=5, stderr=subprocess.DEVNULL
        ).decode()
        for line in out.split("\n"):
            if "CPU die temperature" in line:
                return line.strip()
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            ["osx-cpu-temp"], timeout=3, stderr=subprocess.DEVNULL
        ).decode().strip()
        return f"CPU: {out}"
    except Exception:
        pass

    return None


def ollama_generate(prompt, model=MODEL):
    """Send a generation request to Ollama and return the full response."""
    import urllib.request
    data = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 2048, "temperature": 0.7}
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read())
            return result.get("response", ""), result
    except Exception as e:
        return f"ERROR: {e}", {}


def main():
    print(f"{'='*60}")
    print(f"  Laptop Cooling Stress Test")
    print(f"  Model: {MODEL}")
    print(f"  Prompts: {len(PROMPTS)}")
    print(f"  Start: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")

    # Check Ollama is up
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
    except Exception:
        print("ERROR: Ollama not running. Start with: ollama serve")
        sys.exit(1)

    total_tokens = 0
    rounds = 0
    start_time = time.time()

    try:
        while True:
            for i, prompt in enumerate(PROMPTS):
                rounds += 1
                elapsed = time.time() - start_time
                temp = get_cpu_temp()
                temp_str = f" | {temp}" if temp else ""

                print(f"\n[Round {rounds} | Prompt {i+1}/{len(PROMPTS)} | {elapsed:.0f}s{temp_str}]")
                print(f"  > {prompt[:60]}...")

                gen_start = time.time()
                response, meta = ollama_generate(prompt)
                gen_time = time.time() - gen_start

                tokens = meta.get("eval_count", 0) + meta.get("prompt_eval_count", 0)
                total_tokens += tokens
                tps = tokens / gen_time if gen_time > 0 else 0

                print(f"  ✓ {gen_time:.1f}s | {tokens} tokens | {tps:.1f} tok/s | total: {total_tokens} tokens")

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n\n{'='*60}")
        print(f"  Stress Test Complete")
        print(f"  Duration: {elapsed:.0f}s ({elapsed/60:.1f} min)")
        print(f"  Rounds: {rounds}")
        print(f"  Total tokens: {total_tokens}")
        print(f"  Avg speed: {total_tokens/elapsed:.1f} tok/s")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()

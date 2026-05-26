#!/usr/bin/env python3
"""
Convert Alpaca-format coding dataset to MLX JSONL format.
"""

import json
import random
from datasets import load_dataset

def convert_to_mlx_format(sample):
    """Convert Alpaca format to MLX text format."""
    instruction = sample.get('instruction', '')
    input_text = sample.get('input', '')
    output = sample.get('output', '')

    # Build the text in Alpaca prompt format
    if input_text:
        text = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
    else:
        text = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"

    return {"text": text}

def main():
    print("Loading dataset...")
    ds = load_dataset("iamtarun/python_code_instructions_18k_alpaca")
    train_data = ds['train']

    print(f"Total samples: {len(train_data)}")

    # Shuffle and split
    all_data = list(train_data)
    random.seed(42)
    random.shuffle(all_data)

    # Split: 80% train, 10% valid, 10% test
    n = len(all_data)
    train_end = int(n * 0.8)
    valid_end = int(n * 0.9)

    train_samples = all_data[:train_end]
    valid_samples = all_data[train_end:valid_end]
    test_samples = all_data[valid_end:]

    print(f"Train: {len(train_samples)}, Valid: {len(valid_samples)}, Test: {len(test_samples)}")

    # Convert and save
    splits = {
        'train': train_samples,
        'valid': valid_samples,
        'test': test_samples
    }

    base_dir = "python-code-18k"

    for split_name, samples in splits.items():
        output_file = f"{base_dir}/{split_name}.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for sample in samples:
                mlx_sample = convert_to_mlx_format(sample)
                f.write(json.dumps(mlx_sample, ensure_ascii=False) + '\n')
        print(f"Saved {len(samples)} samples to {output_file}")

    print("\nDone! Now you can fine-tune with:")
    print(f"  mlx_lm lora --model Qwen/Qwen3-9B --data {base_dir}")

if __name__ == "__main__":
    main()

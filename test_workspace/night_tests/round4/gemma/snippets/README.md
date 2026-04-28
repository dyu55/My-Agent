# Text Processor CLI

A simple Python 3.10+ CLI tool for basic text operations.

## Installation
```bash
pip install pytest
```

## Usage
```bash
# Count words
python main.py -i "Hello Python World" count

# Transform case
python main.py --file input.txt transform --mode upper

# Search keyword
python main.py -i "The quick brown fox" search "quick"
```

## Running Tests
```bash
pytest tests/
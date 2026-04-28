# CLI Code Snippet Manager

A lightweight Python CLI tool for managing code snippets using SQLite.

## Features
- Add, list, get, edit, delete, and search code snippets
- JSON-based tag storage
- Type-safe models with Python 3.10+ hints
- SQLite backend with full CRUD support

## Installation
```bash
pip install -e ".[dev]"
```

## Usage
```bash
python -m src.main add -n "hello" -l python -c "print('hi')" -t "basics,gre
"basics,greeting"
python -m src.main list
python -m src.main get 1
python -m src.main edit 1 -n "updated_hello" -t "updated"
python -m src.main delete 1
python -m src.main search "print"
```
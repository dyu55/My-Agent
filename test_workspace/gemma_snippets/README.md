# CLI Code Snippet Manager

A simple CLI tool to store and manage your favorite code snippets.

## Usage

```bash
python src/main.py add "Python Fast API" "python" "print('hello')" "Basic API" "web,fastapi"
python src/main.py list
python src/main.py get 1
python src/main.py search "web"
python src/main.py edit 1 --content "new content"
python src/main.py delete 1
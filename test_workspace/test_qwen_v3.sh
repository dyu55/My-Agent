#!/bin/bash
# Test coding agent capability - generate project

OUTPUT_DIR="/Users/donglingyu/Documents/MyAgent/test_workspace/qwen_output"
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR/snippets/src/snippets/commands"
mkdir -p "$OUTPUT_DIR/snippets/src/snippets/utils"
mkdir -p "$OUTPUT_DIR/snippets/tests"

PROMPT="请为CLI代码片段管理器项目生成完整的Python代码。

项目结构：
- src/main.py: CLI入口，argparse子命令(add/list/get/edit/delete/search)
- src/database.py: SQLite封装，CRUD操作
- src/models.py: 数据模型
- src/commands/: add.py, list.py, get.py, edit.py, delete.py, search.py
- src/utils/: config.py, formatters.py
- tests/: test_database.py, test_models.py
- pyproject.toml, README.md

数据库schema: id, name, language, content, description, tags(JSON), created_at, updated_at

要求：Python 3.10+，类型提示，argparse，sqlite3，pytest

输出格式：每个文件用 ===FILE: 路径 === 分隔，只输出代码，不要解释。"

echo "$PROMPT" | OLLAMA_HOST=192.168.0.124:11434 ollama run qwen3.6:27b-q4_K_M 2>/dev/null > "$OUTPUT_DIR/model_output.txt"

echo "Qwen完成"
wc -c "$OUTPUT_DIR/model_output.txt"

#!/bin/bash
# Test coding agent via Ollama API

OUTPUT_DIR="/Users/donglingyu/Documents/MyAgent/test_workspace/qwen_api_output"
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

curl -s http://192.168.0.124:11434/api/generate -d '{
  "model": "qwen3.6:27b-q4_K_M",
  "prompt": "请为CLI代码片段管理器项目生成完整的Python代码。项目结构：src/main.py (CLI入口,argparse子命令add/list/get/edit/delete/search), src/database.py (SQLite封装), src/models.py (数据模型), src/commands/目录包含add.py,list.py,get.py,edit.py,delete.py,search.py, src/utils/目录包含config.py,formatters.py, tests/目录包含test_database.py,test_models.py, pyproject.toml, README.md。数据库schema: id, name, language, content, description, tags(JSON), created_at, updated_at。要求：Python 3.10+，类型提示，argparse，sqlite3，pytest。输出格式：每个文件用 ===FILE: 路径 === 分隔，只输出代码。",
  "stream": false
}' > "$OUTPUT_DIR/response.json"

echo "Qwen API call completed"
wc -c "$OUTPUT_DIR/response.json"

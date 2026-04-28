#!/bin/bash
# Test coding agent capability - generate project and create files

OUTPUT_DIR="/Users/donglingyu/Documents/MyAgent/test_workspace/gemma_output"
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR/snippets/src/snippets/{commands,utils}
mkdir -p "$OUTPUT_DIR/snippets/tests"

cat << 'PROMPT_EOF' | OLLAMA_HOST=192.168.0.124:11434 ollama run gemma4:31b --thinking 2>/dev/null > "$OUTPUT_DIR/model_output.txt"

请为以下项目生成完整的 Python 代码。输出格式：每个文件用 ===FILE: src/xxx.py=== 分隔（不需要thinking模式输出，直接输出文件内容）。

## 项目：CLI 代码片段管理器 snippets

### 数据库 Schema (SQLite)
```sql
CREATE TABLE IF NOT EXISTS snippets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    language TEXT NOT NULL,
    content TEXT NOT NULL,
    description TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 需要生成的文件：

1. **src/__init__.py** - 包初始化
2. **src/main.py** - CLI 入口，使用 argparse 子命令模式，支持 add/list/get/edit/delete/search 命令
3. **src/database.py** - SQLite 数据库封装，Connection 管理，init_db, add_snippet, get_snippet, list_snippets, update_snippet, delete_snippet, search_snippets 方法
4. **src/models.py** - Snippet 数据类，SnippetResult 枚举
5. **src/commands/__init__.py** - 命令模块初始化
6. **src/commands/add.py** - 添加片段命令实现
7. **src/commands/list.py** - 列出片段命令实现
8. **src/commands/get.py** - 获取片段命令实现
9. **src/commands/edit.py** - 编辑片段命令实现
10. **src/commands/delete.py** - 删除片段命令实现
11. **src/commands/search.py** - 搜索片段命令实现
12. **src/utils/__init__.py** - 工具模块初始化
13. **src/utils/config.py** - 配置管理，~/.snippets/ 目录
14. **src/utils/formatters.py** - 输出格式化
15. **tests/__init__.py** - 测试初始化
16. **tests/test_database.py** - 数据库测试（3个测试用例）
17. **tests/test_models.py** - 模型测试（2个测试用例）
18. **pyproject.toml** - 项目配置
19. **README.md** - 项目说明

### 代码要求：
- Python 3.10+ 类型提示
- argparse 标准库
- sqlite3 标准库
- pytest 测试
- 合理的错误处理

请输出完整的代码。每个文件之间用 ===FILE:=== 分隔。
PROMPT_EOF

echo "Gemma 完成，输出文件数:"
find "$OUTPUT_DIR" -name "*.py" -o -name "*.toml" -o -name "*.md" 2>/dev/null | wc -l

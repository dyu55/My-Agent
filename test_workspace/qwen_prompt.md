# Qwen3.6:27b Coding Agent Test

你是一个专业程序员。请根据以下项目规格，在 `/Users/donglingyu/Documents/MyAgent/test_workspace/qwen_output` 目录下实现一个完整的 CLI 代码片段管理器。

## 项目规格

项目名称: `snippets` - CLI 代码片段管理器

### 核心功能
1. 片段 CRUD: add, list, get, edit, delete, search
2. SQLite 数据库存储 (~/.snippets/snippets.db)
3. 多标签支持 (JSON array)
4. 导入/导出功能
5. 快捷方式/别名配置

### 项目结构
```
snippets/
├── src/
│   ├── __init__.py
│   ├── main.py          # CLI 入口
│   ├── database.py      # SQLite 操作
│   ├── models.py        # 数据模型
│   ├── commands/        # 命令实现
│   │   ├── __init__.py
│   │   ├── add.py
│   │   ├── list.py
│   │   ├── get.py
│   │   ├── edit.py
│   │   ├── delete.py
│   │   └── search.py
│   └── utils/
│       ├── __init__.py
│       ├── config.py
│       └── formatters.py
├── tests/
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_commands.py
│   └── test_models.py
├── pyproject.toml
└── README.md
```

### 技术要求
- Python 3.10+
- 使用 argparse (标准库)
- SQLite (标准库 sqlite3)
- 类型提示
- pytest 测试

### 数据库 Schema
```sql
snippets (
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  language TEXT NOT NULL,
  content TEXT NOT NULL,
  description TEXT,
  tags TEXT,  -- JSON array
  created_at DATETIME,
  updated_at DATETIME
)
```

## 执行步骤

1. 首先创建完整的项目目录结构
2. 实现 database.py - SQLite 封装
3. 实现 models.py - 数据模型
4. 实现 utils/ - 配置和格式化
5. 实现 commands/ - 各命令实现
6. 实现 main.py - CLI 入口
7. 实现测试文件
8. 创建 pyproject.toml 和 README.md

## 验收标准

代码必须:
- 可以正常运行 `python -m snippets list`
- 包含基本的 CRUD 功能
- 有单元测试
- 有合理的错误处理

## 输出要求

请直接创建所有文件，不要解释你的思考过程。完成后报告创建了哪些文件，以及任何需要注意的问题。

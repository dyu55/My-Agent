# Coding Agent Project Spec: CLI 代码片段管理器

## 概述

开发一个 CLI 工具，用于管理和搜索代码片段（snippets）。类似 GitHub Gist 或 VS Code Snippets，但专为命令行用户设计。

## 核心功能

### 1. 片段管理 (CRUD)
- `add <name> <language> --content <code> | --file <path>` - 添加代码片段
- `list [--language <lang>] [--tag <tag>]` - 列出片段
- `get <name>` - 获取片段内容
- `edit <name> [--content <code>] [--tags <tags>]` - 编辑片段
- `delete <name>` - 删除片段
- `search <query>` - 全文搜索片段名称、描述、标签

### 2. 数据存储
- 使用 SQLite 数据库存储片段
- Schema:
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
- 数据库路径: `~/.snippets/snippets.db`

### 3. 标签系统
- 支持多标签 (JSON array)
- 按标签过滤和搜索
- 自动统计标签使用频率

### 4. 导入/导出
- `export [--format json|markdown]` - 导出所有片段
- `import <file>` - 从 JSON 导入片段
- `import-github <username>` - 从 GitHub Gist 导入 (需要 token)

### 5. 快捷方式
- 支持别名/快捷方式
- 配置文件: `~/.snippets/config.yaml`
- 例: `s` = `snippets`

## 技术要求

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

### 依赖
- Python 3.10+
- 标准库: sqlite3, argparse, json, pathlib, datetime
- 可选: pyyaml (配置), requests (GitHub import)
- 测试: pytest

### CLI 框架
- 使用 argparse (标准库, 不依赖外部库)
- 子命令模式

## 质量标准

1. **可运行**: `python -m snippets list` 能正常执行
2. **可测试**: 包含基本单元测试
3. **错误处理**: 合理的错误提示
4. **代码质量**: 清晰的模块划分，类型提示

## 验收测试

1. `snippets add hello python --content "print('hello')"` 成功添加
2. `snippets list` 显示刚添加的片段
3. `snippets get hello` 返回正确内容
4. `snippets search hello` 能找到片段
5. `snippets delete hello` 删除后 `list` 不再显示
6. 单元测试通过

## 复杂度评估

- 6+ 个命令模块
- 数据库抽象层
- 配置文件解析
- JSON 处理
- 错误处理和验证
- 至少 5 个测试用例
- 多文件模块化架构

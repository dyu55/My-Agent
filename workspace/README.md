# TODO 应用

一个基于命令行的任务管理工具，支持添加、删除、标记完成、列出任务、设置优先级和截止日期，数据持久化存储到 JSON 文件。

## 安装

确保已安装 Python 3.8 或更高版本。克隆或下载本项目后，无需额外安装依赖：

```bash
git clone <仓库地址>
cd <项目目录>
```

## 使用方法

运行主程序 `todo.py`，后跟命令和参数：

```bash
python todo.py <命令> [参数]
```

### 命令列表

| 命令      | 说明                   | 示例                                               |
|-----------|------------------------|----------------------------------------------------|
| `add`     | 添加新任务             | `python todo.py add "买菜"`                        |
| `delete`  | 删除指定 ID 的任务     | `python todo.py delete 1`                          |
| `complete`| 标记任务为已完成       | `python todo.py complete 1`                        |
| `list`    | 列出所有任务           | `python todo.py list`                              |
| `priority`| 设置任务的优先级       | `python todo.py priority 1 high`                   |
| `deadline`| 设置任务的截止日期     | `python todo.py deadline 1 2025-12-31`             |

### 参数说明

- `add` 后跟用引号括起来的任务描述。
- `delete`, `complete`, `priority`, `deadline` 的第一个参数是任务 ID。
- `priority` 的第二个参数为 `low`、`medium` 或 `high`。
- `deadline` 的第二个参数为日期，格式 `YYYY-MM-DD`。

## 示例

### 1. 添加任务

```bash
$ python todo.py add "完成报告"
已添加任务: 1 - 完成报告 (待办)
```

### 2. 列出任务

```bash
$ python todo.py list
ID: 1 | 描述: 完成报告 | 状态: 待办 | 优先级: medium | 截止日期: 无 | 创建时间: 2025-01-15 10:30:00
```

### 3. 设置优先级

```bash
$ python todo.py priority 1 high
已更新任务 1 的优先级为 high
```

### 4. 设置截止日期

```bash
$ python todo.py deadline 1 2025-12-31
已更新任务 1 的截止日期为 2025-12-31
```

### 5. 标记完成

```bash
$ python todo.py complete 1
已完成任务: 1
```

### 6. 删除任务

```bash
$ python todo.py delete 1
已删除任务: 1
```

## 项目结构

```
.
├── todo.py              # 主程序入口
├── todo_operations.py   # 任务操作逻辑
├── models/
│   └── todo_item.py     # 数据模型（Task 类）
├── tests/
│   └── test_todo.py     # 单元测试
├── data/
│   └── todos.json       # 数据存储文件（自动生成）
└── README.md            # 本文件
```

## 运行测试

```bash
python -m unittest tests/test_todo.py
```

# My Calculator Agent

这是一个简单的命令行计算器项目，用于演示基本的加减乘除功能。

## 🚀 功能

本项目实现了一个 `Calculator` 类，提供以下核心功能：

*   加法 (`add`)
*   减法 (`subtract`)
*   乘法 (`multiply`)
*   除法 (`divide`) (包含除零异常处理)

## 📁 目录结构

```
. 
├── calculator.py  # 核心计算器逻辑，包含 Calculator 类
├── main.py        # 主运行文件，负责用户交互和调用计算器
├── test_calculator.py # 单元测试文件，确保所有功能和异常处理正确
└── README.md      # 本文档
```

## 🛠️ 安装与运行

本项目不需要额外的依赖，只需 Python 环境。

### 1. 运行主程序 (用户交互模式)

在终端中运行：

```bash
python main.py
```

这将启动一个交互式的计算器界面，您可以输入需要计算的表达式。

### 2. 运行单元测试

为了确保代码的健壮性和准确性，请运行单元测试：

```bash
python -m unittest test_calculator.py
```

## 💡 使用说明

### `calculator.py`

包含 `Calculator` 类，所有业务逻辑集中于此。

### `main.py`

负责用户体验层，处理输入和输出，调用 `Calculator` 的方法。

### `test_calculator.py`

包含所有测试用例，覆盖了正常计算和异常情况（如除零）。

## 🚀 优化与改进

*   **错误处理**: 已经实现了除零异常的捕获。
*   **代码结构**: 遵循了模块化设计，将业务逻辑、主程序和测试分离。
*   **可读性**: 通过添加 Docstrings 和类型提示，提高了代码的可读性和可维护性。
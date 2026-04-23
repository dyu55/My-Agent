# Michael - 本地 Coding Agent

> 用本地 8B/9B 小模型实现能够自主开发完整项目的 Coding Agent。参考 Claude Code 架构。

## 特性

- 🤖 **Claude Code 风格交互** - 直接输入任务描述即可执行
- 💾 **外部记忆模式** - 持久化日志 + Git 版本控制 + 功能清单
- 🔧 **模块化工具系统** - 文件操作、代码执行、搜索、Git、MCP
- 🌐 **多 Provider 支持** - Ollama、OpenAI 兼容 API
- 🔄 **Plan/Act/Reflect 循环** - 任务规划、执行、反思、纠错
- 🧠 **LLM 反思机制** - 自动错误分类和恢复建议

## 快速开始

### 安装

```bash
# Clone 项目
git clone git@github.com:dyu55/My-Agent.git
cd My-Agent

# 安装依赖
pip install -r requirements.txt

# 配置 Ollama (或使用其他 provider)
export OLLAMA_HOST=http://192.168.0.124:11434
export MODEL_NAME=gemma4:latest
```

### 使用

```bash
# 启动交互式 CLI
michael

# 执行单次任务
michael "创建一个 TODO 应用"

# 指定模型
michael -m qwen2.5:9b
```

## 交互模式

```
🎯 实现用户登录功能
🔄 帮我添加注册页面
🔄 /task 添加支付模块
```

### 命令

| 命令 | 说明 |
|------|------|
| `/task <描述>` | 执行任务 |
| `/edit <文件>` | 查看文件 |
| `/run <命令>` | 执行 Shell 命令 |
| `/test` | 运行 pytest |
| `/git <args>` | Git 操作 |
| `/status` | 显示状态 |
| `/help` | 帮助 |
| `/exit` | 退出 |

## 外部记忆模式

当上下文接近上限时，系统会自动提示开启外部记忆模式：

```
/em start          # 开始工作流
/em commit         # 提交更改
/em complete       # 完成并清空上下文
```

### 功能

- 📋 **进度表** - 自动追踪功能和任务进度
- 📝 **会话日志** - 持久化执行过程
- 🔀 **Git 集成** - 自动保存更改
- 💾 **状态恢复** - 从上次中断处继续

## 项目结构

```
MyAgent/
├── agent/                 # Agent 核心
│   ├── engine.py         # Agent 引擎
│   ├── planner.py        # 任务规划
│   ├── executor.py       # 工具执行
│   ├── reflector.py      # 反思纠错
│   └── external_memory_integration.py  # 外部记忆集成
├── cli/                   # CLI
│   ├── michael.py        # Claude Code 风格 CLI
│   └── interface.py      # 经典 CLI
├── memory/                # 外部记忆
│   ├── state_manager.py # 状态管理
│   ├── external_memory.py  # 工作流
│   └── progress.json     # 进度表
├── skills/                # 内置技能
│   ├── code-review       # 代码审查
│   ├── security-review   # 安全审查
│   └── simplify          # 代码简化
├── mcp/                   # MCP 协议
├── utils/                 # 工具函数
└── tests/                 # 测试
```

## 工作流程

```
┌─────────────┐
│ 1. 读取状态  │ ← 从 progress.json 加载任务
├─────────────┤
│ 2. 编写代码  │ ← Agent 执行任务
├─────────────┤
│ 3. 运行测试  │ ← pytest 验证
├─────────────┤
│ 4. Git提交  │ ← 自动暂存+提交
├─────────────┤
│ 5. 清空上下文 │ ← 持久化后释放
└─────────────┘
```

## 配置

### 环境变量

```bash
# Ollama
OLLAMA_HOST=http://192.168.0.124:11434
MODEL_NAME=gemma4:latest

# 或 rsxermu
ACTIVE_PROVIDER=rsxermu
RSXERMU_BASE_URL=https://rsxermu666.cn
RSXERMU_API_KEY=your_key
```

### .env 文件

```bash
cp .env.example .env
# 编辑 .env 填入配置
```

## 开发

```bash
# 运行测试
pytest -v

# 运行特定测试
pytest tests/test_agent.py -v

# 启动开发 CLI
python main.py --chat
```

## 模型推荐

| 模型 | 参数量 | 特点 |
|------|--------|------|
| gemma4:latest | 8B | 快速，GPU 完全加载 |
| gemma4:26b | 26B | 能力强，部分用 RAM |
| qwen2.5:9b | 9B | 中文优化 |

## License

MIT License
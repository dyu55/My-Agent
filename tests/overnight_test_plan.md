# 8 小时通宵测试计划

## 测试目标
全面测试 Michael Agent 的核心功能，涵盖 agent loop、memory system、model providers、CLI 等。

## 环境配置

### 本地模型 (Ollama - 远程服务器 192.168.0.124)
- **Embedding**: 本地 `nomic-embed-text:latest` (274 MB)
- **快速模型**: `qwen3.5:9b` (6.6 GB)
- **复杂任务**: `qwen3.6:27b-coding-nvfp4` (19 GB)
- **通用能力**: `gemma4:26b-nvfp4` (16 GB)

### 远程 API (rsxermu666.cn)
> ⚠️ 注意: 此 API key 仅支持 Anthropic 模型，不支持 GPT/OpenAI 模型
- **Haiku**: `claude-haiku-4-5` (快速，廉价)
- **Sonnet**: `claude-sonnet-4-7` (平衡)
- **Opus**: `claude-opus-4-7` (最强推理)

### Codex 配置参考
Codex 使用 GPT-5.5/GPT-5.4 模型 (需要 ChatGPT Plus OAuth 认证):
```
model_provider = "OpenAI"
model = "gpt-5.5"
review_model = "gpt-5.4"
wire_api = "responses"
```

## 测试阶段

### Phase 1: 基础功能测试 (0-1h)
```
[00:00-00:15] Agent 初始化和配置加载
[00:15-00:30] Tool executor 基础操作 (read, write, edit, mkdir, list_dir)
[00:30-00:45] Task planner 任务分解
[00:45-01:00] Result reflector 错误分类和恢复
```

### Phase 2: Memory System 测试 (1-2h)
```
[01:00-01:20] Embedding 生成和存储
[01:20-01:40] 语义搜索 (recall)
[01:40-02:00] 标签过滤和会话管理
```

### Phase 3: Model Provider 测试 (2-4h)
```
[02:00-02:30] Ollama provider (远程服务器模型切换)
[02:30-03:00] 远程 API 测试 (rsxermu666.cn - Sonnet/Haiku)
[03:00-03:30] 模型降级和错误恢复
[03:30-04:00] 并发请求处理
```

### Phase 4: CLI 集成测试 (4-5h)
```
[04:00-04:30] 交互式 CLI 模式
[04:30-05:00] 命令解析和执行
```

### Phase 5: 端到端工作流 (5-7h)
```
[05:00-05:30] 完整项目创建流程
[05:30-06:00] 多轮对话上下文保持
[06:00-06:30] 错误处理和恢复
[06:30-07:00] 记忆持久化和检索
```

### Phase 6: 压力测试 (7-8h)
```
[07:00-07:30] 长时间运行稳定性
[07:30-08:00] 内存泄漏检测和资源清理
```

## 测试执行命令

### Phase 1: 基础功能
```bash
# Agent 初始化测试
python3 -c "
from agent.engine import AgentEngine
from agent.planner import TaskPlanner
from agent.executor import ToolExecutor
from agent.reflector import ResultReflector

# 测试初始化
engine = AgentEngine()
planner = TaskPlanner()
executor = ToolExecutor()
reflector = ResultReflector()

print('✓ Agent components initialized')

# 测试任务分解
task = 'Create a simple calculator that can add, subtract, multiply, divide'
plan = planner.create_plan(task)
print(f'✓ Task decomposed into {len(plan.subtasks)} subtasks')
"

# 运行单元测试
python3 -m pytest tests/test_agent.py tests/test_planner.py tests/test_executor.py -v --tb=short
```

### Phase 2: Memory System
```bash
python3 -m pytest tests/test_memory_interface.py tests/test_layer1_integration.py -v --tb=short

# 手动验证 embedding
python3 -c "
from memory.embedding_store import EmbeddingStore
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    store = EmbeddingStore(store_dir=tmpdir)
    
    # 测试 remember
    id1 = store.remember(content='Python is a great language', tags=['code', 'python'])
    id2 = store.remember(content='JavaScript for web', tags=['code', 'js'])
    
    # 测试 recall
    results = store.recall(query='programming language', limit=5)
    print(f'✓ Embedding generated: {len(results)} results')
    
    # 测试统计
    stats = store.get_stats()
    print(f'✓ Stats: {stats[\"total_memories\"]} memories, {stats[\"total_tags\"]} tags')
"
```

### Phase 3: Model Provider
```bash
# 测试 Ollama provider (远程服务器)
python3 -c "
from utils.model_provider import ModelProviderFactory

# 测试远程服务器连接
provider = ModelProviderFactory.create('ollama', base_url='http://192.168.0.124:11434')
print(f'✓ Ollama provider connected: {provider.base_url}')

# 测试模型列表
models = provider.list_models()
print(f'✓ Available models: {len(models)}')
for m in models[:5]:
    print(f'  - {m.name}')
"

# 测试远程 API (Claude Sonnet/Haiku)
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

RSXERMU_BASE_URL = os.getenv('RSXERMU_BASE_URL', 'https://rsxermu666.cn')
RSXERMU_API_KEY = os.getenv('RSXERMU_API_KEY', '')

import requests

# 测试 Claude Sonnet
response = requests.post(
    f'{RSXERMU_BASE_URL}/v1/messages',
    headers={
        'Authorization': f'Bearer {RSXERMU_API_KEY}',
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01'
    },
    json={
        'model': 'claude-sonnet-4-7',
        'max_tokens': 100,
        'messages': [{'role': 'user', 'content': 'Say hello in 5 words'}]
    }
)
if response.status_code == 200:
    print('✓ Claude Sonnet 4 API working')
else:
    print(f'✗ Claude Sonnet failed: {response.text}')

# 测试 Claude Haiku
response = requests.post(
    f'{RSXERMU_BASE_URL}/v1/messages',
    headers={
        'Authorization': f'Bearer {RSXERMU_API_KEY}',
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01'
    },
    json={
        'model': 'claude-haiku-4-5',
        'max_tokens': 100,
        'messages': [{'role': 'user', 'content': 'Say hello in 5 words'}]
    }
)
if response.status_code == 200:
    print('✓ Claude Haiku 4 API working')
else:
    print(f'✗ Claude Haiku failed: {response.text}')
"

# 测试各模型响应
python3 main.py "Say hello in 10 words" --model qwen3.5:9b --provider ollama --base-url http://192.168.0.124:11434

python3 main.py "Explain what a neural network is in one sentence" --model qwen3.6:27b-coding-nvfp4 --provider ollama --base-url http://192.168.0.124:11434
```

### Phase 4: CLI 集成
```bash
# 测试 CLI 帮助
python3 main.py --help

# 测试 chat 模式 (自动化)
echo -e "exit" | python3 main.py --chat --model qwen3.5:9b
```

### Phase 5: 端到端工作流
```bash
# 创建测试项目
python3 main.py "Create a TODO CLI app in Python with pytest"

# 测试多轮对话
python3 main.py --chat << 'EOF'
Create a simple hello world function
Add a test for it
Run the test
exit
EOF
```

### Phase 6: 压力测试
```bash
# 内存监控
python3 -c "
import psutil
import os
import time

process = psutil.Process(os.getpid())
print(f'Initial memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')

from agent.engine import AgentEngine
engine = AgentEngine()

# 模拟多轮调用
for i in range(100):
    try:
        engine.execute('Say hello')
        if i % 10 == 0:
            print(f'Round {i}: {process.memory_info().rss / 1024 / 1024:.1f} MB')
    except Exception as e:
        print(f'Error at round {i}: {e}')
        break

print(f'Final memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"
```

## 监控指标

### 每小时检查点
```bash
# 内存使用
ps aux | grep python | grep -v grep

# CPU 使用
top -l 1 | grep python

# 磁盘 I/O
iostat 1 5

# 测试覆盖率
python3 -m pytest --cov=. --cov-report=term-missing --cov-report=html | head -50
```

### 关键日志
- `/Users/donglingyu/Documents/MyAgent/logs/` 下的执行日志
- `memory/` 目录的索引文件

## 预期结果
- 所有单元测试通过
- Integration 测试通过率 > 90%
- 无内存泄漏 (< 100MB 增长)
- 所有 model provider 正常工作
- CLI 所有命令可用

## 失败处理
- 单个测试失败 → 记录并继续
- 连续失败 → 触发告警
- 内存泄漏检测 → 自动重启
- 网络断开 → 自动重连

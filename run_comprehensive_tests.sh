#!/bin/bash
# MyAgent 综合测试运行器 - 6小时深度测试
# 覆盖: 核心引擎 | 工具系统 | 外部记忆 | 高级功能 | 模型适配 | 端到端

set -e

# ==================== 配置 ====================
OLLAMA_HOST="http://192.168.0.124:11434"
MODEL_NAME="qwen3.5:9b"
WORKSPACE="workspace/comprehensive_test"
RESULTS_FILE="logs/comprehensive_results.json"
LOG_FILE="logs/comprehensive_test.log"

# 测试配置
TIMEOUT_TASK=600      # 单任务超时: 10分钟
TIMEOUT_COMPLEX=1200  # 复杂任务超时: 20分钟

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# ==================== 工具函数 ====================
log() { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"; }
pass() { echo -e "${GREEN}[✓]${NC} $1"; }
fail() { echo -e "${RED}[✗]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
phase() { echo -e "\n${PURPLE}══════════════════════════════════════════${NC}"; echo -e "${PURPLE}  $1${NC}"; echo -e "${PURPLE}══════════════════════════════════════════${NC}\n"; }
task() { echo -e "${CYAN}▶ $1${NC}"; }

# ==================== 初始化 ====================
init() {
    log "初始化测试环境..."
    export OLLAMA_HOST="$OLLAMA_HOST"
    export MODEL_NAME="$MODEL_NAME"
    export ACTIVE_PROVIDER=ollama

    mkdir -p "$WORKSPACE" "logs"

    # 确认模型
    if curl -s --connect-timeout 5 "$OLLAMA_HOST/api/tags" | grep -q "qwen"; then
        pass "模型连接: $MODEL_NAME"
    else
        fail "无法连接 Ollama 服务器"
        exit 1
    fi

    # 初始化结果
    cat > "$RESULTS_FILE" <<EOF
{
  "start_time": "$(date -Iseconds)",
  "phases": {},
  "tests": []
}
EOF

    pass "初始化完成"
}

# ==================== 任务执行 ====================
run_task() {
    local phase=$1
    local test_id=$2
    local description=$3
    local timeout=${4:-$TIMEOUT_TASK}
    local validation=$5

    task "[$test_id] $description"
    local start=$(date +%s)

    # 执行任务
    cd ~/Documents/MyAgent

    local output
    if timeout "$timeout" python main.py --model "$MODEL_NAME" --provider ollama "$description" >/dev/null 2>&1; then
        local end=$(date +%s)
        local duration=$((end - start))
        pass "完成 (${duration}秒)"

        # 验证
        if [ -n "$validation" ]; then
            if eval "$validation"; then
                pass "验证通过"
            else
                warn "验证失败"
            fi
        fi

        # 记录
        jq ".tests += [{\"id\":\"$test_id\",\"phase\":\"$phase\",\"status\":\"pass\",\"duration\":$duration}]" "$RESULTS_FILE" > /tmp/results.json && mv /tmp/results.json "$RESULTS_FILE"
    else
        local exit_code=$?
        local end=$(date +%s)
        local duration=$((end - start))

        if [ $exit_code -eq 124 ]; then
            fail "超时 (${timeout}秒)"
            jq ".tests += [{\"id\":\"$test_id\",\"phase\":\"$phase\",\"status\":\"timeout\",\"duration\":$duration}]" "$RESULTS_FILE" > /tmp/results.json && mv /tmp/results.json "$RESULTS_FILE"
        else
            fail "失败 (退出码: $exit_code)"
            jq ".tests += [{\"id\":\"$test_id\",\"phase\":\"$phase\",\"status\":\"fail\",\"duration\":$duration}]" "$RESULTS_FILE" > /tmp/results.json && mv /tmp/results.json "$RESULTS_FILE"
        fi
    fi

    sleep 3
}

# ==================== 阶段A: 核心引擎 ====================
phase_a() {
    phase "阶段A: 核心引擎测试 (60分钟)"

    # A1: 规划器测试
    echo -e "\n${CYAN}[A1] 规划器深度测试${NC}\n"

    run_task "A" "A1.1" "将'创建用户认证系统，包含注册、登录、登出，使用JWT'分解为子任务"
    run_task "A" "A1.2" "将'创建Django博客项目'分解，识别模型和路由依赖"
    run_task "A" "A1.3" "将'创建微服务架构，包含用户、订单、支付服务'分解，生成并行任务"
    run_task "A" "A1.4" "分析'重构混乱项目'的最佳策略"

    # A2: 执行器测试
    echo -e "\n${CYAN}[A2] 执行器测试${NC}\n"

    run_task "A" "A2.1" "在 $WORKSPACE/executor_test/ 创建 utils.py 实现日志功能"
    run_task "A" "A2.2" "创建目录结构: src/, tests/, docs/, 包含 __init__.py"
    run_task "A" "A2.3" "执行 'python -c print(1+1)' 并捕获输出"
    run_task "A" "A2.4" "运行 pytest 10秒超时测试"

    # A3: 反射器测试
    echo -e "\n${CYAN}[A3] 反射器测试${NC}\n"

    run_task "A" "A3.1" "分析包含语法错误的代码并修复"
    run_task "A" "A3.2" "处理 'python main.py --invalid-option' 失败并恢复"
    run_task "A" "A3.3" "修复排序算法中的逻辑错误"
    run_task "A" "A3.4" "检测并替换不存在的 npm 包"

    jq ".phases.A = {\"total\":12,\"passed\":$(grep -c '\"status\":\"pass\"' "$RESULTS_FILE" || echo 0)}" "$RESULTS_FILE" > /tmp/results.json && mv /tmp/results.json "$RESULTS_FILE"
}

# ==================== 阶段B: 工具系统 ====================
phase_b() {
    phase "阶段B: 工具系统测试 (120分钟)"

    # B1: 文件操作
    echo -e "\n${CYAN}[B1] 文件操作工具${NC}\n"

    run_task "B" "B1.1a" "创建 $WORKSPACE/file_ops/test.py 内容为 'print(\"hello\")'"
    run_task "B" "B1.1b" "读取 $WORKSPACE/file_ops/test.py 内容"
    run_task "B" "B1.1c" "在 test.py 末尾添加 '# added by agent'"
    run_task "B" "B1.1d" "创建批量文件: README.md, setup.py, src/__init__.py, requirements.txt"
    run_task "B" "B1.2" "修改 $WORKSPACE/file_ops/test.py 中两处不同代码"

    # B2: 执行工具
    echo -e "\n${CYAN}[B2] 执行工具${NC}\n"

    run_task "B" "B2.1" "运行 'echo hello && echo world' 并验证输出"
    run_task "B" "B2.2" "运行 'find . -name \"*.py\" | head -5'"
    run_task "B" "B2.3" "检查项目依赖是否完整 (pip list)"
    run_task "B" "B2.4" "为 $WORKSPACE/exec_test/calculator.py 编写单元测试"

    # B3: 搜索工具
    echo -e "\n${CYAN}[B3] 搜索工具${NC}\n"

    run_task "B" "B3.1" "搜索项目中的所有 TODO 和 FIXME"
    run_task "B" "B3.2" "搜索所有 print 语句"
    run_task "B" "B3.3" "搜索 'Flask REST API 最佳实践'"

    # B4: Git操作
    echo -e "\n${CYAN}[B4] Git操作${NC}\n"

    run_task "B" "B4.1" "在 $WORKSPACE/git_test/ 初始化Git仓库，创建初始提交"
    run_task "B" "B4.2" "创建 feature 分支，添加文件并提交，合并回 main"
    run_task "B" "B4.3" "分析项目 Git 状态和最近提交"

    # B5: 质量工具
    echo -e "\n${CYAN}[B5] 质量工具${NC}\n"

    run_task "B" "B5.1" "对 $WORKSPACE/quality_test/ 代码运行 pylint"
    run_task "B" "B5.2" "为项目添加类型注解并运行 mypy"

    # B6: 部署工具
    echo -e "\n${CYAN}[B6] 部署工具${NC}\n"

    run_task "B" "B6.1" "为 $WORKSPACE/deploy_test/ 项目创建 Dockerfile"
    run_task "B" "B6.2" "创建 GitHub Actions CI 工作流 (lint + test)"

    jq ".phases.B = {\"total\":18,\"passed\":$(grep -c '\"phase\":\"B\",\"status\":\"pass\"' "$RESULTS_FILE" || echo 0)}" "$RESULTS_FILE" > /tmp/results.json && mv /tmp/results.json "$RESULTS_FILE"
}

# ==================== 阶段C: 外部记忆 ====================
phase_c() {
    phase "阶段C: 外部记忆测试 (60分钟)"

    # C1: 会话记忆
    echo -e "\n${CYAN}[C1] 会话记忆${NC}\n"

    run_task "C" "C1.1" "创建 User 类，然后添加 email 属性，验证上下文保持"
    run_task "C" "C1.2" "连续执行5个小任务，观察上下文压缩"

    # C2: 向量搜索
    echo -e "\n${CYAN}[C2] 向量搜索${NC}\n"

    run_task "C" "C2.1" "将 docs/ 目录的文档存入向量数据库"
    run_task "C" "C2.2" "搜索 '用户认证相关' 文档"
    run_task "C" "C2.3" "搜索 '部署配置' 语义相关文档"

    # C3: 跨会话学习
    echo -e "\n${CYAN}[C3] 跨会话学习${NC}\n"

    run_task "C" "C3.1" "执行文件操作任务，观察模式是否保存"
    run_task "C" "C3.2" "执行新任务，观察是否自动回忆历史模式"

    jq ".phases.C = {\"total\":8,\"passed\":$(grep -c '\"phase\":\"C\",\"status\":\"pass\"' "$RESULTS_FILE" || echo 0)}" "$RESULTS_FILE" > /tmp/results.json && mv /tmp/results.json "$RESULTS_FILE"
}

# ==================== 阶段D: 高级功能 ====================
phase_d() {
    phase "阶段D: 高级功能测试 (90分钟)"

    # D1: MCP集成
    echo -e "\n${CYAN}[D1] MCP集成${NC}\n"

    run_task "D" "D1.1" "连接 MCP 文件系统服务器"
    run_task "D" "D1.2" "使用 MCP 列出 ~/Documents/MyAgent 目录"
    run_task "D" "D1.3" "使用 MCP 读取 agent/engine.py 的前20行"

    # D2: Skills系统
    echo -e "\n${CYAN}[D2] Skills系统${NC}\n"

    run_task "D" "D2.1" "对 $WORKSPACE/skills_test/ 运行 /code-review"
    run_task "D" "D2.2" "对 $WORKSPACE/skills_test/ 运行 /security-review"
    run_task "D" "D2.3" "运行 /simplify 简化代码"
    run_task "D" "D2.4" "创建自定义 Skill 'api-test' 自动测试 API"

    # D3: 流式进度
    echo -e "\n${CYAN}[D3] 流式进度${NC}\n"

    run_task "D" "D3.1" "执行一个包含5个子任务的项目创建，观察流式进度显示"
    run_task "D" "D3.2" "验证彩色日志输出正确"

    # D4: 多Agent协调
    echo -e "\n${CYAN}[D4] 多Agent协调${NC}\n"

    run_task "D" "D4.1" "并行执行3个独立任务: 前端/后端/测试"
    run_task "D" "D4.2" "执行有依赖关系的任务链"

    jq ".phases.D = {\"total\":12,\"passed\":$(grep -c '\"phase\":\"D\",\"status\":\"pass\"' "$RESULTS_FILE" || echo 0)}" "$RESULTS_FILE" > /tmp/results.json && mv /tmp/results.json "$RESULTS_FILE"
}

# ==================== 阶段E: 模型适配 ====================
phase_e() {
    phase "阶段E: 模型适配测试 (45分钟)"

    # E1: 结构化输出
    echo -e "\n${CYAN}[E1] 结构化输出${NC}\n"

    run_task "E" "E1.1" "让模型生成有效的 JSON 格式响应"
    run_task "E" "E1.2" "测试 JSON 解析失败时的回退机制"

    # E2: Chain-of-Thought
    echo -e "\n${CYAN}[E2] Chain-of-Thought${NC}\n"

    run_task "E" "E2.1" "让模型解释其任务分解的决策过程"
    run_task "E" "E2.2" "提供 few-shot 示例后执行类似任务"

    # E3: 错误恢复
    echo -e "\n${CYAN}[E3] 错误恢复${NC}\n"

    run_task "E" "E3.1" "触发任务连续失败3次，观察恢复策略"
    run_task "E" "E3.2" "测试部分成功场景的处理"

    jq ".phases.E = {\"total\":6,\"passed\":$(grep -c '\"phase\":\"E\",\"status\":\"pass\"' "$RESULTS_FILE" || echo 0)}" "$RESULTS_FILE" > /tmp/results.json && mv /tmp/results.json "$RESULTS_FILE"
}

# ==================== 阶段F: 端到端 ====================
phase_f() {
    phase "阶段F: 端到端测试 (45分钟)"

    # F1: 完整项目
    echo -e "\n${CYAN}[F1] 完整博客系统${NC}\n"

    run_task "F" "F1.1" "在 $WORKSPACE/blog_system/ 创建完整博客系统:
      - app.py (Flask主应用)
      - models/ (user, post, comment)
      - routes/ (auth, posts, users)
      - templates/ (base, index, post)
      - tests/ (单元测试)
      - requirements.txt
      支持: 用户注册登录, 文章CRUD, 评论, Markdown渲染" $TIMEOUT_COMPLEX

    # F2: Bug修复
    echo -e "\n${CYAN}[F2] Bug修复场景${NC}\n"

    run_task "F" "F2.1" "修复博客系统的以下问题:
      1. 用户可删除他人文章
      2. 评论提交后页面不刷新
      3. 搜索返回空结果" $TIMEOUT_COMPLEX

    jq ".phases.F = {\"total\":2,\"passed\":$(grep -c '\"phase\":\"F\",\"status\":\"pass\"' "$RESULTS_FILE" || echo 0)}" "$RESULTS_FILE" > /tmp/results.json && mv /tmp/results.json "$RESULTS_FILE"
}

# ==================== 生成报告 ====================
generate_report() {
    phase "生成测试报告"

    local end_time=$(date -Iseconds)
    local total=$(grep -c '"status"' "$RESULTS_FILE" || echo 0)
    local passed=$(grep -c '"status":"pass"' "$RESULTS_FILE" || echo 0)
    local failed=$(grep -c '"status":"fail"' "$RESULTS_FILE" || echo 0)
    local timeout=$(grep -c '"status":"timeout"' "$RESULTS_FILE" || echo 0)
    local rate=$((passed * 100 / total))

    jq ".end_time = \"$end_time\" | .summary = {\"total\":$total,\"passed\":$passed,\"failed\":$failed,\"timeout\":$timeout,\"rate\":\"$rate%\"}" "$RESULTS_FILE" > /tmp/results.json && mv /tmp/results.json "$RESULTS_FILE"

    echo ""
    pass "测试完成!"
    echo ""
    echo "========================================"
    echo "  测试结果汇总"
    echo "========================================"
    echo "  总任务数: $total"
    echo "  通过:     $passed"
    echo "  失败:     $failed"
    echo "  超时:     $timeout"
    echo "  通过率:   $rate%"
    echo "========================================"
    echo ""
    echo "详细结果: $RESULTS_FILE"
    echo "运行日志: $LOG_FILE"
}

# ==================== 主函数 ====================
main() {
    echo "=============================================="
    echo "   MyAgent 综合测试 - 6小时深度测试"
    echo "   模型: $MODEL_NAME"
    echo "   服务器: $OLLAMA_HOST"
    echo "=============================================="
    echo ""

    init
    phase_a
    phase_b
    phase_c
    phase_d
    phase_e
    phase_f
    generate_report
}

# 参数处理
case "${1:-all}" in
    --phase)
        case "$2" in
            A) phase_a ;;
            B) phase_b ;;
            C) phase_c ;;
            D) phase_d ;;
            E) phase_e ;;
            F) phase_f ;;
            *) echo "可用阶段: A B C D E F"; exit 1 ;;
        esac
        ;;
    all) main ;;
    *) echo "用法: $0 [--phase A|B|C|D|E|F]"; exit 1 ;;
esac
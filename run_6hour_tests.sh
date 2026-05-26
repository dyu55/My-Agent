#!/bin/bash
# MyAgent 6小时自动化测试脚本
# 使用 qwen3.5:9b 远程模型测试

set -e

# 配置
OLLAMA_HOST="http://192.168.0.124:11434"
MODEL_NAME="qwen3.5:9b"
WORKSPACE_DIR="workspace/6hour_test"
RESULTS_FILE="logs/6hour_test_results.json"
LOG_FILE="logs/6hour_test.log"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_step() {
    echo -e "${BLUE}==>${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

echo_error() {
    echo -e "${RED}[✗]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# 初始化
init() {
    echo_step "初始化测试环境..."

    # 创建工作目录
    mkdir -p "$WORKSPACE_DIR"
    mkdir -p "logs"

    # 设置环境变量
    export OLLAMA_HOST="$OLLAMA_HOST"
    export MODEL_NAME="$MODEL_NAME"

    # 确认模型可用
    echo_step "检查模型连接..."
    if curl -s --connect-timeout 5 "$OLLAMA_HOST/api/tags" | grep -q "qwen3.5"; then
        echo_success "模型连接正常: $MODEL_NAME"
    else
        echo_error "无法连接到远程 Ollama"
        echo "请检查网络连接和 Ollama 服务状态"
        exit 1
    fi

    # 初始化结果记录
    echo '{"start_time":"'$(date -Iseconds)'","tasks":[],"summary":{}}' > "$RESULTS_FILE"

    echo_success "初始化完成"
    echo ""
}

# 运行单个任务
run_task() {
    local task_id=$1
    local task_name=$2
    local task_desc=$3
    local timeout=${4:-600}  # 默认10分钟超时

    echo_step "[$task_id] $task_name"
    echo "    描述: $task_desc"

    local start_time=$(date +%s)

    # 运行任务
    cd ~/Documents/MyAgent

    if timeout "$timeout" python main.py --model "$MODEL_NAME" --provider ollama "$task_desc" 2>&1 | tee -a "$LOG_FILE"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        local result="success"

        echo_success "[$task_id] 完成 (${duration}秒)"
    else
        local exit_code=$?
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        if [ $exit_code -eq 124 ]; then
            local result="timeout"
            echo_warning "[$task_id] 超时 (${timeout}秒)"
        else
            local result="error"
            echo_error "[$task_id] 失败 (退出码: $exit_code)"
        fi
    fi

    # 记录结果
    local result_json=$(cat <<EOF
{"id":"$task_id","name":"$task_name","duration":$duration,"result":"$result"}
EOF
)
    echo ","$result_json >> "$RESULTS_FILE"

    echo ""
    sleep 5  # 任务间隔
}

# 阶段1: 简单任务
phase1_simple() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}阶段1: 简单任务 (8个任务, ~1小时)${NC}"
    echo -e "${BLUE}========================================${NC}\n"

    run_task "T1.1" "Hello World" "在 $WORKSPACE_DIR 创建 hello.py，输出 'Hello, World!'"
    run_task "T1.2" "简单计算器" "在 $WORKSPACE_DIR 创建 calculator.py，实现 add(a,b) 和 multiply(a,b) 函数"
    run_task "T1.3" "文件追加" "在 $WORKSPACE_DIR/hello.py 末尾添加注释 '# Modified by MyAgent'"
    run_task "T1.4" "列表去重" "在 $WORKSPACE_DIR 创建 list_utils.py，实现 unique() 函数去除列表重复元素"
    run_task "T1.5" "字符串反转" "在 $WORKSPACE_DIR 创建 string_utils.py，实现 reverse_string() 函数"
    run_task "T1.6" "基础测试" "为 $WORKSPACE_DIR/calculator.py 编写单元测试，保存到 test_calculator.py"
    run_task "T1.7" "字典合并" "在 $WORKSPACE_DIR 创建 dict_utils.py，实现 merge_dicts() 合并两个字典"
    run_task "T1.8" "日志记录" "在 $WORKSPACE_DIR 创建 logger.py，实现简单的日志类 Logger"
}

# 阶段2: 中等任务
phase2_medium() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}阶段2: 中等任务 (6个任务, ~2小时)${NC}"
    echo -e "${BLUE}========================================${NC}\n"

    run_task "T2.1" "TODO应用" "在 $WORKSPACE_DIR 创建 todo/ 目录，开发一个命令行 TODO 应用，支持 add/list/done 命令，数据保存到 tasks.json" 1200
    run_task "T2.2" "HTTP服务器" "在 $WORKSPACE_DIR 创建 flask_server.py，实现 Flask HTTP 服务器，包含 GET /hello、GET /time、POST /echo 路由" 1200
    run_task "T2.3" "单元测试套件" "为 $WORKSPACE_DIR/string_utils.py 编写完整的单元测试，覆盖所有函数" 900
    run_task "T2.4" "数据验证器" "在 $WORKSPACE_DIR 创建 validator.py，实现 validate_email()、validate_phone()、validate_url() 函数" 1200
    run_task "T2.5" "配置管理器" "在 $WORKSPACE_DIR 创建 config.py，支持从 JSON 文件加载配置和环境变量覆盖" 1200
    run_task "T2.6" "Markdown解析器" "在 $WORKSPACE_DIR 创建 markdown.py，解析 # 标题、**粗体**、- 列表、链接语法" 1500
}

# 阶段3: 复杂任务
phase3_complex() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}阶段3: 复杂任务 (4个任务, ~2.5小时)${NC}"
    echo -e "${BLUE}========================================${NC}\n"

    run_task "T3.1" "记事本应用" "在 $WORKSPACE_DIR 创建 notepad.py，使用 Tkinter 创建记事本应用，支持新建/打开/保存文件和基本编辑功能" 2400
    run_task "T3.2" "REST API项目" "在 $WORKSPACE_DIR/api_project/ 创建 Flask REST API，包含 app.py、models.py、routes.py、config.py，实现完整的用户 CRUD 接口" 2700
    run_task "T3.3" "测试框架" "在 $WORKSPACE_DIR 创建 mytest.py，实现简单的测试框架，包含 @test 装饰器和 assert_equal 等断言" 2100
    run_task "T3.4" "代码分析器" "在 $WORKSPACE_DIR 创建 code_analyzer.py，统计代码行数、检测 TODO/FIXME、生成分析报告" 1800
}

# 生成报告
generate_report() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}生成测试报告${NC}"
    echo -e "${BLUE}========================================${NC}\n"

    local end_time=$(date -Iseconds)
    echo "\"end_time\":\"$end_time\"" >> "$RESULTS_FILE"
    echo "}" >> "$RESULTS_FILE"

    echo_success "测试完成!"
    echo ""
    echo "结果日志: $LOG_FILE"
    echo "结果JSON: $RESULTS_FILE"

    # 显示统计
    echo ""
    echo_step "测试统计:"
    echo "    总任务: 18"
    echo "    检查日志获取详细结果"
}

# 主函数
main() {
    echo "=============================================="
    echo "   MyAgent 6小时测试"
    echo "   模型: $MODEL_NAME"
    echo "   服务器: $OLLAMA_HOST"
    echo "=============================================="
    echo ""

    init
    phase1_simple
    phase2_medium
    phase3_complex
    generate_report
}

# 运行
main
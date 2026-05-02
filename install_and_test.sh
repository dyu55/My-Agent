#!/bin/bash
# Install dependencies and verify MyAgent skills system

set -e

echo "=========================================="
echo "🔧 MyAgent 安装与验证脚本"
echo "=========================================="
echo ""

# 1. 安装依赖
echo "📦 安装 Python 依赖..."
pip install playwright beautifulsoup4 requests -q
echo "✅ 依赖安装完成"
echo ""

# 2. 安装 Playwright 浏览器
echo "🌐 安装 Playwright Chromium..."
playwright install chromium
echo "✅ Chromium 安装完成"
echo ""

# 3. 运行测试
echo "🧪 运行测试套件..."
echo ""
python3 tests/test_skills_comprehensive.py
echo ""

# 4. 运行浏览器工具测试
echo "🧪 运行浏览器工具测试..."
python3 tests/test_browser_tools.py -v
echo ""

echo "=========================================="
echo "✅ 安装与验证完成！"
echo "=========================================="
#!/bin/bash
# Linux/Mac快速启动脚本

echo "========================================"
echo "HPC论文自动获取工具"
echo "========================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.7+"
    exit 1
fi

# 检查依赖
if ! python3 -c "import feedparser" 2>/dev/null; then
    echo "正在安装依赖..."
    pip3 install -r requirements.txt
fi

echo ""
echo "选择运行模式:"
echo "1. 手动运行一次"
echo "2. 启动定时任务"
echo ""
read -p "请输入选项 (1 或 2): " choice

if [ "$choice" == "1" ]; then
    echo ""
    echo "正在运行..."
    python3 main.py --days 1 --config config.json
elif [ "$choice" == "2" ]; then
    echo ""
    echo "正在启动定时任务..."
    python3 scheduler.py
else
    echo "无效选项"
fi

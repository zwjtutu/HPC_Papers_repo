@echo off
REM Windows快速启动脚本
echo ========================================
echo HPC论文自动获取工具
echo ========================================
echo.

REM 检查是否安装了Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

REM 检查是否安装了依赖
echo 检查依赖...
pip show feedparser >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
)

echo.
echo 选择运行模式:
echo 1. 手动运行一次
echo 2. 启动定时任务
echo.
set /p choice=请输入选项 (1 或 2): 

if "%choice%"=="1" (
    echo.
    echo 正在运行...
    python main.py --days 1 --config config.json
) else if "%choice%"=="2" (
    echo.
    echo 正在启动定时任务...
    python scheduler.py
) else (
    echo 无效选项
)

pause

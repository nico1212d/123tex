@echo off
CHCP 65001

echo 正在启动 MaiBot Core...
echo 正在启动主程序...

REM 使用项目自带的 Python 环境
set "PYTHON_PATH=%~dp0runtime\python31211\bin\python.exe"

REM 检查项目自带的 Python 是否存在
if not exist "%PYTHON_PATH%" (
    echo 错误：找不到项目自带的 Python 环境
    echo 路径：%PYTHON_PATH%
    echo 请确认 runtime\python31211\bin\python.exe 文件存在
    pause
    exit /b 1
)

echo 使用项目自带的 Python: %PYTHON_PATH%

REM 验证 Python 版本
"%PYTHON_PATH%" -c "import sys; print(f'Python 版本: {sys.version}'); exit(0) if sys.version_info[0] == 3 and sys.version_info[1] >= 11 else exit(1)"
if %ERRORLEVEL% neq 0 (
    echo 错误：Python 版本不符合要求
    pause
    exit /b 1
)

:start
"%PYTHON_PATH%" start.py
pause
@echo off
CHCP 65001

echo 正在启动 OpenIE导入程序...

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
echo.
echo 请注意：此脚本将导入OpenIE文件.
echo 请确保你的数据库已启动并运行.
echo 如果没有，请运行"![启动点我！！！.bat"这个脚本启动主程序.
echo.
set /p "confirm=您确定要继续吗? (y/n): "
if /i not "%confirm%"=="y" (
    echo 操作已取消。
    goto :eof
)
"%PYTHON_PATH%" ".\modules\MaiBot\scripts\import_openie.py"
echo.
pause
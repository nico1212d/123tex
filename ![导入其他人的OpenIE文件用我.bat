@echo off
CHCP 65001

echo 正在启动 OpenIE导入程序...
REM 检查虚拟环境是否存在且可用
if exist "venv" (
    echo 检测到现有虚拟环境，正在检查是否可用...
    call venv\Scripts\activate.bat
    python -c "import sys; exit(0) if sys.version_info[0] == 3 and sys.version_info[1] == 12 else exit(1)" && (
        echo 虚拟环境可用
        goto :start
    )
    echo 虚拟环境不可用，将创建新的虚拟环境
    rmdir /s /q venv
)

echo 正在创建虚拟环境...
"%PYTHON_PATH%" -m venv venv
call venv\Scripts\activate.bat



:start
echo.
echo 请注意：此脚本将导入OpenIE文件.
echo 请确保你的MongoDB数据库已启动并运行.
echo 如果没有，请运行"![启动点我！！！.bat"这个脚本.并选择选项2.
echo.
set /p "confirm=您确定要继续吗? (y/n): "
if /i not "%confirm%"=="y" (
    echo 操作已取消。
    goto :eof
)
python .\scripts\import_openie.py
echo.
pause
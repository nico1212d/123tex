@echo off
chcp 65001 >nul
title 更新所有模块

echo =====================================================================
echo  模块更新工具 （提示：如果出现更新失败的错误，请尝试右键管理员运行本脚本！）
echo =====================================================================
echo.

REM 设置Python路径
set "PYTHON_PATH=%~dp0runtime\python31211\bin\python.exe"

REM 检查Python是否存在
if exist "%PYTHON_PATH%" (
    echo 使用内置Python: %PYTHON_PATH%
) else (
    echo 错误：未找到内置Python.
    echo 路径: %PYTHON_PATH%
    pause
    exit /b 1
)
echo.

REM 运行更新脚本
echo 开始执行更新脚本...
"%PYTHON_PATH%" "%~dp0\update_modules.py"

echo.
if %errorlevel% equ 0 (
    echo 更新完成！.
) else (
    echo 更新过程中出现错误！.
)
echo 按任意键退出...
pause >nul

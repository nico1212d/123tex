@echo off
chcp 65001 >nul
title 更新所有模块

echo ================================================
echo                  模块更新工具
echo ================================================
echo.

REM 直接使用内置Python
if exist "runtime\python31211\bin\python.exe" (
    set PYTHON_CMD=runtime\python31211\bin\python.exe
    echo 使用内置Python: %PYTHON_CMD%
) else (
    echo 错误：未找到内置Python (runtime\python31211\bin\python.exe)
    pause
    exit /b 1
)
echo.

REM 运行更新脚本
%PYTHON_CMD% update_modules.py

echo.
echo 按任意键退出...
pause >nul

@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo        仅更新一键包仓库
echo ========================================
echo.
echo 正在启动一键包仓库更新...
echo.

rem 使用内置Python运行更新脚本，只更新一键包仓库
"runtime\python31211\python.exe" update_modules.py --only-onekey

echo.
echo ========================================
echo 按任意键退出...
echo ========================================
pause >nul

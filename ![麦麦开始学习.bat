@echo off
CHCP 65001 > nul
setlocal enabledelayedexpansion

echo 正在启动麦麦学习流程...

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

echo 环境已成功验证！开始学习流程...

REM --- 麦麦学习脚本执行 ---

REM 运行预处理脚本
echo 正在执行数据预处理...
"%PYTHON_PATH%" "%~dp0modules\MaiBot\scripts\raw_data_preprocessor.py"
if %ERRORLEVEL% neq 0 (
    echo 错误: raw_data_preprocessor.py 执行失败.
    pause
    exit /b 1
)

REM 运行信息提取脚本
echo 正在执行信息提取...
"%PYTHON_PATH%" "%~dp0modules\MaiBot\scripts\info_extraction.py"
if %ERRORLEVEL% neq 0 (
    echo 错误: info_extraction.py 执行失败.
    pause
    exit /b 1
)

REM 运行OpenIE导入脚本
echo 正在导入OpenIE数据...
"%PYTHON_PATH%" "%~dp0modules\MaiBot\scripts\import_openie.py"
if %ERRORLEVEL% neq 0 (
    echo 错误: import_openie.py 执行失败.
    pause
    exit /b 1
)

echo 🎉 麦麦学习流程已完成！
pause
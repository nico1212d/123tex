@echo off
setlocal enabledelayedexpansion

chcp 65001 >nul

REM 检测是否在压缩包内运行
set "CURRENT_PATH=%~dp0"
echo %CURRENT_PATH% | findstr /i "temp" >nul && set "IN_ARCHIVE=1" || set "IN_ARCHIVE=0"
echo %CURRENT_PATH% | findstr /i "tmp" >nul && set "IN_ARCHIVE=1"
echo %CURRENT_PATH% | findstr /i "rar$" >nul && set "IN_ARCHIVE=1"
echo %CURRENT_PATH% | findstr /i "zip$" >nul && set "IN_ARCHIVE=1"
echo %CURRENT_PATH% | findstr /i "7z$" >nul && set "IN_ARCHIVE=1"

if "%IN_ARCHIVE%"=="1" (
    echo -   
    echo ==========================================.
    echo        我草，你是不是脑子有坑啊？
    echo ==========================================.
    echo -
    echo 你™直接在压缩包里运行脚本？你是天才还是傻逼？.
    echo 这种操作也就你能想得出来，孙笑川都得给你磕一个！.
    echo -
    echo 你™不知道解压吗？小学没毕业？.
    echo -
    echo 赶紧给老子滚去解压！.
    echo 要不然程序出了问题，老子可不管！.
    echo -
    echo 操你妈的，赶紧按任意键给老子滚蛋！.
    echo ==========================================.
    echo -
    echo 按任意键退出，然后给老子滚去解压！.
    echo 以上所有文字由Gemini AI生成，如果有任何不满，请投诉Gemini谢谢.
    pause >nul
    exit /b 1
)

REM 保存当前目录
set "CURRENT_DIR=%CD%"

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

:choose_pip_source
echo.
echo 请选择pip下载源:
echo 1. 阿里云 (https://mirrors.aliyun.com/pypi/simple) [推荐]
echo 2. 清华 (https://pypi.tuna.tsinghua.edu.cn/simple)
echo 3. 豆瓣 (https://pypi.douban.com/simple)
echo 4. 官方 (https://pypi.org/simple)
set /p PIP_SRC_CHOICE=请输入数字选择 [1-4]，回车默认1:
if "%PIP_SRC_CHOICE%"=="" set PIP_SRC_CHOICE=1
if "%PIP_SRC_CHOICE%"=="1" set PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
if "%PIP_SRC_CHOICE%"=="2" set PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
if "%PIP_SRC_CHOICE%"=="3" set PIP_INDEX_URL=https://pypi.douban.com/simple
if "%PIP_SRC_CHOICE%"=="4" set PIP_INDEX_URL=https://pypi.org/simple

:install_deps
REM 更新 pip
echo 正在更新 pip...
"%PYTHON_PATH%" -m pip install -i %PIP_INDEX_URL% --upgrade pip

REM 安装依赖
echo 正在安装依赖...
"%PYTHON_PATH%" -m pip install -i %PIP_INDEX_URL% -r modules\MaiBot\requirements.txt --upgrade

REM 调用init_napcat.py更新配置
echo 正在初始化 NapCat 配置...
"%PYTHON_PATH%" init_napcat.py

echo 安装完成！请运行启动脚本！

REM 调用config_manager.py
echo 正在启动配置管理器...
"%PYTHON_PATH%" config_manager.py
echo.

pause
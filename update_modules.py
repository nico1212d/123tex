# -*- coding: utf-8 -*-
"""
模块更新脚本
功能：更新所有模块的git仓库并安装依赖包
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, cwd=None, description=""):
    """执行命令"""
    try:
        if description:
            print(f"正在执行: {description}")
        print(f"命令: {command} (目录: {cwd if cwd else '当前目录'})")
        
        # 设置环境变量以确保正确的编码
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['LANG'] = 'zh_CN.UTF-8'
        
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',  # 忽略编码错误
            env=env
        )
        
        if result.returncode == 0:
            if result.stdout and result.stdout.strip():
                print(f"✅ 成功: {result.stdout.strip()}")
            else:
                print("✅ 成功")
            return True
        else:
            error_msg = result.stderr.strip() if result.stderr else "未知错误"
            print(f"❌ 错误: {error_msg}")
            return False
    except Exception as e:
        print(f"❌ 执行命令时发生异常: {e}")
        return False

def run_git_command(repo_path, command):
    """在指定目录执行git命令"""
    return run_command(command, repo_path)

def install_requirements(repo_path, repo_name):
    """安装requirements.txt中的依赖"""
    requirements_file = os.path.join(repo_path, 'requirements.txt')
    
    if not os.path.exists(requirements_file):
        print(f"📋 {repo_name} 没有requirements.txt文件，跳过依赖安装")
        return True
    
    print(f"\n{'='*40}")
    print(f"正在安装 {repo_name} 的依赖")
    print(f"{'='*40}")
    
    # 获取Python可执行文件路径
    python_cmd = sys.executable    # 安装依赖（使用阿里云镜像源，禁用进度条避免编码问题）
    install_cmd = f'"{python_cmd}" -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --upgrade --no-color --disable-pip-version-check --progress-bar off'
    success = run_command(install_cmd, repo_path, f"安装 {repo_name} 依赖")
    
    if success:
        print(f"✅ {repo_name} 依赖安装完成")
    else:
        print(f"❌ {repo_name} 依赖安装失败")
    
    return success

def update_repository(repo_path, repo_name):
    """更新单个仓库"""
    print(f"\n{'='*50}")
    print(f"正在更新 {repo_name}")
    print(f"路径: {repo_path}")
    print(f"{'='*50}")
    
    if not os.path.exists(repo_path):
        print(f"❌ 错误: 仓库路径不存在: {repo_path}")
        return False
    
    if not os.path.exists(os.path.join(repo_path, '.git')):
        print(f"❌ 错误: 不是git仓库: {repo_path}")
        return False
    
    # 检查git状态
    print("检查仓库状态...")
    if not run_git_command(repo_path, "git status --porcelain"):
        return False
    
    # 获取当前分支
    print("获取当前分支...")
    result = subprocess.run(
        "git branch --show-current",
        cwd=repo_path,
        shell=True,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    
    if result.returncode == 0:
        current_branch = result.stdout.strip()
        print(f"当前分支: {current_branch}")
    else:
        print("无法获取当前分支")
        current_branch = "main"
    
    # 执行git pull
    print("正在拉取最新代码...")
    success = run_git_command(repo_path, "git pull")
    
    if success:
        print(f"✅ {repo_name} 更新完成")
    else:
        print(f"❌ {repo_name} 更新失败")
    
    return success

def main():
    """主函数"""
    print("开始更新所有模块...")
    print(f"当前工作目录: {os.getcwd()}")
    
    # 获取脚本所在目录（项目根目录）
    script_dir = Path(__file__).parent.absolute()
    
    # 定义要更新的仓库
    repositories = [
        {
            'name': '一键包主仓库',
            'path': script_dir
        },
        {
            'name': 'MaiBot主仓库',
            'path': script_dir / 'modules' / 'MaiBot'
        },
        {
            'name': 'MaiBot-Napcat-Adapter适配器仓库',
            'path': script_dir / 'modules' / 'MaiBot-Napcat-Adapter'
        }
    ]
    
    total_count = len(repositories)
    update_success_count = 0
    install_success_count = 0
    
    # 第一阶段：逐个更新仓库
    print(f"\n{'='*60}")
    print("第一阶段：更新Git仓库")
    print(f"{'='*60}")
    
    for repo in repositories:
        if update_repository(str(repo['path']), repo['name']):
            update_success_count += 1
    
    # 第二阶段：安装依赖
    print(f"\n{'='*60}")
    print("第二阶段：安装依赖包")
    print(f"{'='*60}")
    
    for repo in repositories:
        if install_requirements(str(repo['path']), repo['name']):
            install_success_count += 1
    
    # 输出总结
    print(f"\n{'='*60}")
    print(f"更新完成！Git更新: {update_success_count}/{total_count}")
    print(f"依赖安装: {install_success_count}/{total_count}")
    print(f"{'='*60}")
    
    if update_success_count == total_count and install_success_count == total_count:
        print("🎉 所有模块更新和依赖安装成功！")
        return 0
    elif update_success_count == total_count:
        print("✅ 所有模块更新成功，但部分依赖安装失败")
        return 1
    else:
        print("⚠️  部分模块更新失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n程序执行过程中发生未知错误: {e}")
        sys.exit(1)

# -*- coding: utf-8 -*-
"""
模块更新脚本
功能：更新所有模块的git仓库
"""

import os
import subprocess
import sys
from pathlib import Path

def run_git_command(repo_path, command):
    """在指定目录执行git命令"""
    try:
        print(f"正在执行: {command} (目录: {repo_path})")
        result = subprocess.run(
            command,
            cwd=repo_path,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            print(f"✅ 成功: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ 错误: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ 执行命令时发生异常: {e}")
        return False

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
    
    success_count = 0
    total_count = len(repositories)
    
    # 逐个更新仓库
    for repo in repositories:
        if update_repository(str(repo['path']), repo['name']):
            success_count += 1
    
    # 输出总结
    print(f"\n{'='*60}")
    print(f"更新完成！成功: {success_count}/{total_count}")
    print(f"{'='*60}")
    
    if success_count == total_count:
        print("🎉 所有模块更新成功！")
        return 0
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

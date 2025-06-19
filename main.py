# -*- coding: utf-8 -*-
import os
import re
import sys
import subprocess
from pathlib import Path

def is_first_run() -> bool:
    """检查是否是首次运行"""
    # 标记文件路径: 主程序目录/runtime/.gitkeep
    marker = Path(__file__).parent / "runtime" / ".gitkeep"
    
    if not marker.exists():
        # 首次运行：创建runtime目录和标记文件
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()  # 创建空文件
        return True
    
    return False

def run_python_script(script_name: str):
    """运行同一目录下的Python脚本"""
    # 获取当前脚本目录
    current_dir = Path(__file__).parent
    
    # 构建目标脚本路径
    target_script = current_dir / script_name
    
    # 获取Python解释器的路径（使用原始字符串）
    python_path = os.path.abspath(r"./runtime/python31211/bin/python.exe")
    
    try:
        # 执行目标脚本（注意参数格式）
        subprocess.run([python_path, str(target_script)])
        return True
    except Exception as e:
        print(f"执行出错：{str(e)}")
        return False

def check_dir_legal():
    """检查当前目录是否包含中文"""
    # 获取当前工作目录
    current_path = os.getcwd()
    # 检查路径是否包含中文字符（Unicode范围）
    has_chinese = bool(re.search(r'[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]', current_path))
    # 检查当前目录是否包含中文字符
    if has_chinese:
        print(f"警告：当前路径包含中文等特殊字符: {current_path}")
        print("禁止启动，已自动退出，请将一键包移动到非中文目录再启动！")
        return True
    else:
        return False

if __name__ == "__main__":
    if not check_dir_legal():
        # 检查是否首次运行
        if is_first_run():
            # 初始化一键包
            print("首次运行一键包，执行初始化操作……")
            run_python_script("update_modules.py")
            print("======================")
            print("正在执行NapCat初始化脚本...")
            print("======================")
            run_python_script("init_napcat.py")
            print("======================")
            print("正在执行MaiBot初始化脚本...")
            print("======================")
            run_python_script("config_manager.py")
        else:
            try:
                print("正在启动 MaiBot Core...")
                run_python_script("start.py")
            except Exception as e:
                print(f"启动主程序出错：{str(e)}")
            
    else:
        # 直接退出
        sys.exit()
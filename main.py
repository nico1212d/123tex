# -*- coding: utf-8 -*-
import os
import re
import sys
import subprocess
try:
    from modules.MaiBot.src.common.logger import get_logger
    logger = get_logger("init")
except ImportError:
    import logger
    logger.basicConfig(level=logger.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logger.getLogger("init")

from pathlib import Path
from typing import Optional

# 配置日志

def get_python_interpreter() -> Optional[Path]:
    """获取Python解释器路径"""
    try:
        # 尝试多个可能的路径
        possible_paths = [
            Path(__file__).parent / "runtime" / "python31211" / "bin" / "python.exe",
            Path(__file__).parent / "runtime" / "python31211" / "python.exe",
            Path(sys.executable),  # 当前Python解释器
        ]
        
        for python_path in possible_paths:
            if python_path.exists() and python_path.is_file():
                logger.info(f"找到Python解释器: {python_path}")
                return python_path
        
        logger.error("未找到可用的Python解释器")
        return None
        
    except Exception as e:
        logger.error(f"获取Python解释器路径时出错: {e}")
        return None

def is_first_run() -> bool:
    """检查是否是首次运行"""
    try:
        # 标记文件路径: 主程序目录/runtime/.gitkeep
        marker = Path(__file__).parent / "runtime" / ".gitkeep"
        
        if not marker.exists():
            # 首次运行：创建runtime目录和标记文件
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.touch()  # 创建空文件
            logger.info("检测到首次运行，已创建标记文件")
            return True
        
        logger.info("检测到非首次运行")
        return False
        
    except Exception as e:
        logger.error(f"检查首次运行状态时出错: {e}")
        # 出错时默认为首次运行，确保初始化能正常进行
        return True

def run_python_script(script_name: str) -> bool:
    """运行同一目录下的Python脚本"""
    try:
        # 获取当前脚本目录
        current_dir = Path(__file__).parent
        
        # 构建目标脚本路径
        target_script = current_dir / script_name
        
        # 检查目标脚本是否存在
        if not target_script.exists():
            logger.error(f"目标脚本不存在: {target_script}")
            return False
        
        # 获取Python解释器路径
        python_path = get_python_interpreter()
        if python_path is None:
            logger.error("无法找到Python解释器")
            return False
        
        logger.info(f"开始执行脚本: {script_name}")
        
        # 执行目标脚本
        result = subprocess.run(
            [str(python_path), str(target_script)],
            capture_output=False,  # 保持输出到控制台
            text=True,
            timeout=300,  # 5分钟超时
            cwd=str(current_dir)  # 设置工作目录
        )
        
        if result.returncode == 0:
            logger.info(f"脚本执行成功: {script_name}")
            return True
        else:
            logger.error(f"脚本执行失败: {script_name}, 返回码: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"脚本执行超时: {script_name}")
        return False
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {e}")
        return False
    except Exception as e:
        logger.error(f"执行脚本时出错: {script_name}, 错误: {e}")
        return False

def safe_system_command(command: str, timeout: int = 30) -> bool:
    """安全地执行系统命令
    
    Args:
        command: 要执行的命令
        timeout: 超时时间（秒）
        
    Returns:
        bool: 命令执行是否成功
    """
    try:
        logger.info(f"执行系统命令: {command}")
        result = subprocess.run(
            command,
            shell=True,
            timeout=timeout,
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"系统命令执行成功: {command}")
            return True
        else:
            logger.warning(f"系统命令执行失败: {command}, 返回码: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"系统命令执行超时: {command}")
        return False
    except Exception as e:
        logger.error(f"执行系统命令时出错: {command}, 错误: {e}")
        return False

def check_dir_legal() -> bool:
    """检查当前目录是否包含中文等特殊字符
    
    Returns:
        bool: True表示目录包含非法字符，False表示目录合法
    """
    try:
        # 获取当前工作目录
        current_path = os.getcwd()
        
        # 检查路径是否包含中文字符（Unicode范围）
        has_chinese = bool(re.search(r'[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]', current_path))
        
        if has_chinese:
            error_msg = f"警告：当前路径包含中文等特殊字符: {current_path}"
            print(error_msg)
            print("禁止启动，已自动退出，请将一键包移动到非中文目录再启动！")
            logger.error(error_msg)
            logger.error("程序因路径包含特殊字符而退出")
            return True
        else:
            logger.info(f"路径检查通过: {current_path}")
            return False
            
    except Exception as e:
        error_msg = f"检查目录路径时出错: {e}"
        print(error_msg)
        logger.error(error_msg)
        # 出错时为安全起见，认为路径不合法
        return True

def main() -> None:
    """主函数"""
    try:
        logger.info("MaiBot 一键包启动")
        
        # 检查目录路径合法性
        if check_dir_legal():
            logger.error("目录路径不合法，程序退出")
            sys.exit(1)
        
        # 检查是否首次运行
        if is_first_run():
            # 初始化一键包
            logger.info("首次运行一键包，执行初始化操作")
            print("首次运行一键包，执行初始化操作……")
            
            if not run_python_script("update_modules.py"):
                logger.error("模块更新失败")
                return
                
            print("======================")
            print("正在执行NapCat初始化脚本...")
            print("======================")
            
            if not run_python_script("init_napcat.py"):
                logger.error("NapCat初始化失败")
                return
                
            print("======================")
            print("正在执行MaiBot初始化脚本...")
            print("======================")
            
            if not run_python_script("config_manager.py"):
                logger.error("MaiBot配置失败")
                return
                
            print("3秒后启动MaiBot Client...")
            safe_system_command("timeout /t 3 /nobreak > nul")
            safe_system_command("cls")
            
            if not run_python_script("main.py"):
                logger.error("MaiBot启动失败")
                return
        else:
            # 非首次运行
            logger.info("检测到不是首次运行，正在跳过向导启动 MaiBot Core")
            print("检测到不是首次运行，正在跳过向导启动 MaiBot Core...")
            
            if not run_python_script("start.py"):
                logger.error("启动主程序失败")
                return
                
        logger.info("程序执行完成")
        
    except KeyboardInterrupt:
        logger.info("用户中断程序执行")
        print("\n程序已被用户中断")
    except Exception as e:
        logger.error(f"程序执行过程中出现未知错误: {e}")
        print(f"程序执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
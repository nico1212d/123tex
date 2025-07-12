from fastapi import HTTPException
from rich.traceback import install
from src.config.config import get_config_dir, load_config
from src.common.logger import get_logger
import os

install(extra_lines=3)

logger = get_logger("api")


async def reload_config():
    try:
        from src.config import config as config_module

        logger.debug("正在重载配置文件...")
        bot_config_path = os.path.join(get_config_dir(), "bot_config.toml")
        config_module.global_config = load_config(config_path=bot_config_path)
        logger.debug("配置文件重载成功")
        return {"status": "reloaded"}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重载配置时发生错误: {str(e)}") from e

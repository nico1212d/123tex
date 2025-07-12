from src.llm_models.utils_model import LLMRequest
from src.config.config import global_config
import time
from src.common.logger import get_logger
from src.chat.utils.prompt_builder import Prompt, global_prompt_manager
from src.tools.tool_use import ToolUser
from src.chat.utils.json_utils import process_llm_tool_calls
from typing import List, Dict, Tuple, Optional

logger = get_logger("tool_executor")


def init_tool_executor_prompt():
    """初始化工具执行器的提示词"""
    tool_executor_prompt = """
你是一个专门执行工具的助手。你的名字是{bot_name}。现在是{time_now}。
群里正在进行的聊天内容：
{chat_history}

现在，{sender}发送了内容:{target_message},你想要回复ta。
请仔细分析聊天内容，考虑以下几点：
1. 内容中是否包含需要查询信息的问题
2. 是否有明确的工具使用指令

If you need to use a tool, please directly call the corresponding tool function. If you do not need to use any tool, simply output "No tool needed".
"""
    Prompt(tool_executor_prompt, "tool_executor_prompt")


class ToolExecutor:
    """独立的工具执行器组件

    可以直接输入聊天消息内容，自动判断并执行相应的工具，返回结构化的工具执行结果。
    """

    def __init__(self, chat_id: str = None, enable_cache: bool = True, cache_ttl: int = 3):
        """初始化工具执行器

        Args:
            executor_id: 执行器标识符，用于日志记录
            enable_cache: 是否启用缓存机制
            cache_ttl: 缓存生存时间（周期数）
        """
        self.chat_id = chat_id
        self.log_prefix = f"[ToolExecutor:{self.chat_id}] "
        self.llm_model = LLMRequest(
            model=global_config.model.tool_use,
            request_type="tool_executor",
        )

        # 初始化工具实例
        self.tool_instance = ToolUser()

        # 缓存配置
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.tool_cache = {}  # 格式: {cache_key: {"result": result, "ttl": ttl, "timestamp": timestamp}}

        logger.info(f"{self.log_prefix}工具执行器初始化完成，缓存{'启用' if enable_cache else '禁用'}，TTL={cache_ttl}")

    async def execute_from_chat_message(
        self, target_message: str, chat_history: list[str], sender: str, return_details: bool = False
    ) -> List[Dict] | Tuple[List[Dict], List[str], str]:
        """从聊天消息执行工具

        Args:
            target_message: 目标消息内容
            chat_history: 聊天历史
            sender: 发送者
            return_details: 是否返回详细信息(使用的工具列表和提示词)

        Returns:
            如果return_details为False: List[Dict] - 工具执行结果列表
            如果return_details为True: Tuple[List[Dict], List[str], str] - (结果列表, 使用的工具, 提示词)
        """

        # 首先检查缓存
        cache_key = self._generate_cache_key(target_message, chat_history, sender)
        cached_result = self._get_from_cache(cache_key)

        if cached_result:
            logger.info(f"{self.log_prefix}使用缓存结果，跳过工具执行")
            if return_details:
                # 从缓存结果中提取工具名称
                used_tools = [result.get("tool_name", "unknown") for result in cached_result]
                return cached_result, used_tools, "使用缓存结果"
            else:
                return cached_result

        # 缓存未命中，执行工具调用
        # 获取可用工具
        tools = self.tool_instance._define_tools()

        # 获取当前时间
        time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        bot_name = global_config.bot.nickname

        # 构建工具调用提示词
        prompt = await global_prompt_manager.format_prompt(
            "tool_executor_prompt",
            target_message=target_message,
            chat_history=chat_history,
            sender=sender,
            bot_name=bot_name,
            time_now=time_now,
        )

        logger.debug(f"{self.log_prefix}开始LLM工具调用分析")

        # 调用LLM进行工具决策
        response, other_info = await self.llm_model.generate_response_async(prompt=prompt, tools=tools)

        # 解析LLM响应
        if len(other_info) == 3:
            reasoning_content, model_name, tool_calls = other_info
        else:
            reasoning_content, model_name = other_info
            tool_calls = None

        # 执行工具调用
        tool_results, used_tools = await self._execute_tool_calls(tool_calls)

        # 缓存结果
        if tool_results:
            self._set_cache(cache_key, tool_results)

        logger.info(f"{self.log_prefix}工具执行完成，共执行{len(used_tools)}个工具: {used_tools}")

        if return_details:
            return tool_results, used_tools, prompt
        else:
            return tool_results

    async def _execute_tool_calls(self, tool_calls) -> Tuple[List[Dict], List[str]]:
        """执行工具调用

        Args:
            tool_calls: LLM返回的工具调用列表

        Returns:
            Tuple[List[Dict], List[str]]: (工具执行结果列表, 使用的工具名称列表)
        """
        tool_results = []
        used_tools = []

        if not tool_calls:
            logger.debug(f"{self.log_prefix}无需执行工具")
            return tool_results, used_tools

        logger.info(f"{self.log_prefix}开始执行工具调用: {tool_calls}")

        # 处理工具调用
        success, valid_tool_calls, error_msg = process_llm_tool_calls(tool_calls)

        if not success:
            logger.error(f"{self.log_prefix}工具调用解析失败: {error_msg}")
            return tool_results, used_tools

        if not valid_tool_calls:
            logger.debug(f"{self.log_prefix}无有效工具调用")
            return tool_results, used_tools

        # 执行每个工具调用
        for tool_call in valid_tool_calls:
            try:
                tool_name = tool_call.get("name", "unknown_tool")
                used_tools.append(tool_name)

                logger.debug(f"{self.log_prefix}执行工具: {tool_name}")

                # 执行工具
                result = await self.tool_instance._execute_tool_call(tool_call)

                if result:
                    tool_info = {
                        "type": result.get("type", "unknown_type"),
                        "id": result.get("id", f"tool_exec_{time.time()}"),
                        "content": result.get("content", ""),
                        "tool_name": tool_name,
                        "timestamp": time.time(),
                    }
                    tool_results.append(tool_info)

                    logger.info(f"{self.log_prefix}工具{tool_name}执行成功，类型: {tool_info['type']}")
                    logger.debug(f"{self.log_prefix}工具{tool_name}结果内容: {tool_info['content'][:200]}...")

            except Exception as e:
                logger.error(f"{self.log_prefix}工具{tool_name}执行失败: {e}")
                # 添加错误信息到结果中
                error_info = {
                    "type": "tool_error",
                    "id": f"tool_error_{time.time()}",
                    "content": f"工具{tool_name}执行失败: {str(e)}",
                    "tool_name": tool_name,
                    "timestamp": time.time(),
                }
                tool_results.append(error_info)

        return tool_results, used_tools

    def _generate_cache_key(self, target_message: str, chat_history: list[str], sender: str) -> str:
        """生成缓存键

        Args:
            target_message: 目标消息内容
            chat_history: 聊天历史
            sender: 发送者

        Returns:
            str: 缓存键
        """
        import hashlib

        # 使用消息内容和群聊状态生成唯一缓存键
        content = f"{target_message}_{chat_history}_{sender}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """从缓存获取结果

        Args:
            cache_key: 缓存键

        Returns:
            Optional[List[Dict]]: 缓存的结果，如果不存在或过期则返回None
        """
        if not self.enable_cache or cache_key not in self.tool_cache:
            return None

        cache_item = self.tool_cache[cache_key]
        if cache_item["ttl"] <= 0:
            # 缓存过期，删除
            del self.tool_cache[cache_key]
            logger.debug(f"{self.log_prefix}缓存过期，删除缓存键: {cache_key}")
            return None

        # 减少TTL
        cache_item["ttl"] -= 1
        logger.debug(f"{self.log_prefix}使用缓存结果，剩余TTL: {cache_item['ttl']}")
        return cache_item["result"]

    def _set_cache(self, cache_key: str, result: List[Dict]):
        """设置缓存

        Args:
            cache_key: 缓存键
            result: 要缓存的结果
        """
        if not self.enable_cache:
            return

        self.tool_cache[cache_key] = {"result": result, "ttl": self.cache_ttl, "timestamp": time.time()}
        logger.debug(f"{self.log_prefix}设置缓存，TTL: {self.cache_ttl}")

    def _cleanup_expired_cache(self):
        """清理过期的缓存"""
        if not self.enable_cache:
            return

        expired_keys = []
        for cache_key, cache_item in self.tool_cache.items():
            if cache_item["ttl"] <= 0:
                expired_keys.append(cache_key)

        for key in expired_keys:
            del self.tool_cache[key]

        if expired_keys:
            logger.debug(f"{self.log_prefix}清理了{len(expired_keys)}个过期缓存")

    def get_available_tools(self) -> List[str]:
        """获取可用工具列表

        Returns:
            List[str]: 可用工具名称列表
        """
        tools = self.tool_instance._define_tools()
        return [tool.get("function", {}).get("name", "unknown") for tool in tools]

    async def execute_specific_tool(
        self, tool_name: str, tool_args: Dict, validate_args: bool = True
    ) -> Optional[Dict]:
        """直接执行指定工具

        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            validate_args: 是否验证参数

        Returns:
            Optional[Dict]: 工具执行结果，失败时返回None
        """
        try:
            tool_call = {"name": tool_name, "arguments": tool_args}

            logger.info(f"{self.log_prefix}直接执行工具: {tool_name}")

            result = await self.tool_instance._execute_tool_call(tool_call)

            if result:
                tool_info = {
                    "type": result.get("type", "unknown_type"),
                    "id": result.get("id", f"direct_tool_{time.time()}"),
                    "content": result.get("content", ""),
                    "tool_name": tool_name,
                    "timestamp": time.time(),
                }
                logger.info(f"{self.log_prefix}直接工具执行成功: {tool_name}")
                return tool_info

        except Exception as e:
            logger.error(f"{self.log_prefix}直接工具执行失败 {tool_name}: {e}")

        return None

    def clear_cache(self):
        """清空所有缓存"""
        if self.enable_cache:
            cache_count = len(self.tool_cache)
            self.tool_cache.clear()
            logger.info(f"{self.log_prefix}清空了{cache_count}个缓存项")

    def get_cache_status(self) -> Dict:
        """获取缓存状态信息

        Returns:
            Dict: 包含缓存统计信息的字典
        """
        if not self.enable_cache:
            return {"enabled": False, "cache_count": 0}

        # 清理过期缓存
        self._cleanup_expired_cache()

        total_count = len(self.tool_cache)
        ttl_distribution = {}

        for cache_item in self.tool_cache.values():
            ttl = cache_item["ttl"]
            ttl_distribution[ttl] = ttl_distribution.get(ttl, 0) + 1

        return {
            "enabled": True,
            "cache_count": total_count,
            "cache_ttl": self.cache_ttl,
            "ttl_distribution": ttl_distribution,
        }

    def set_cache_config(self, enable_cache: bool = None, cache_ttl: int = None):
        """动态修改缓存配置

        Args:
            enable_cache: 是否启用缓存
            cache_ttl: 缓存TTL
        """
        if enable_cache is not None:
            self.enable_cache = enable_cache
            logger.info(f"{self.log_prefix}缓存状态修改为: {'启用' if enable_cache else '禁用'}")

        if cache_ttl is not None and cache_ttl > 0:
            self.cache_ttl = cache_ttl
            logger.info(f"{self.log_prefix}缓存TTL修改为: {cache_ttl}")


# 初始化提示词
init_tool_executor_prompt()


"""
使用示例：

# 1. 基础使用 - 从聊天消息执行工具（启用缓存，默认TTL=3）
executor = ToolExecutor(executor_id="my_executor")
results = await executor.execute_from_chat_message(
    talking_message_str="今天天气怎么样？现在几点了？",
    is_group_chat=False
)

# 2. 禁用缓存的执行器
no_cache_executor = ToolExecutor(executor_id="no_cache", enable_cache=False)

# 3. 自定义缓存TTL
long_cache_executor = ToolExecutor(executor_id="long_cache", cache_ttl=10)

# 4. 获取详细信息
results, used_tools, prompt = await executor.execute_from_chat_message(
    talking_message_str="帮我查询Python相关知识",
    is_group_chat=False,
    return_details=True
)

# 5. 直接执行特定工具
result = await executor.execute_specific_tool(
    tool_name="get_knowledge",
    tool_args={"query": "机器学习"}
)

# 6. 缓存管理
available_tools = executor.get_available_tools()
cache_status = executor.get_cache_status()  # 查看缓存状态
executor.clear_cache()  # 清空缓存
executor.set_cache_config(cache_ttl=5)  # 动态修改缓存配置
"""

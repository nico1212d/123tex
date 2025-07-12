"""
消息API模块

提供消息查询和构建成字符串的功能，采用标准Python包设计模式
使用方式：
    from src.plugin_system.apis import message_api
    messages = message_api.get_messages_by_time_in_chat(chat_id, start_time, end_time)
    readable_text = message_api.build_readable_messages(messages)
"""

from typing import List, Dict, Any, Tuple, Optional
import time
from src.chat.utils.chat_message_builder import (
    get_raw_msg_by_timestamp,
    get_raw_msg_by_timestamp_with_chat,
    get_raw_msg_by_timestamp_with_chat_inclusive,
    get_raw_msg_by_timestamp_with_chat_users,
    get_raw_msg_by_timestamp_random,
    get_raw_msg_by_timestamp_with_users,
    get_raw_msg_before_timestamp,
    get_raw_msg_before_timestamp_with_chat,
    get_raw_msg_before_timestamp_with_users,
    num_new_messages_since,
    num_new_messages_since_with_users,
    build_readable_messages,
    build_readable_messages_with_list,
    get_person_id_list,
)


# =============================================================================
# 消息查询API函数
# =============================================================================


def get_messages_by_time(
    start_time: float, end_time: float, limit: int = 0, limit_mode: str = "latest"
) -> List[Dict[str, Any]]:
    """
    获取指定时间范围内的消息

    Args:
        start_time: 开始时间戳
        end_time: 结束时间戳
        limit: 限制返回的消息数量，0为不限制
        limit_mode: 当limit>0时生效，'earliest'表示获取最早的记录，'latest'表示获取最新的记录

    Returns:
        消息列表
    """
    return get_raw_msg_by_timestamp(start_time, end_time, limit, limit_mode)


def get_messages_by_time_in_chat(
    chat_id: str, start_time: float, end_time: float, limit: int = 0, limit_mode: str = "latest"
) -> List[Dict[str, Any]]:
    """
    获取指定聊天中指定时间范围内的消息

    Args:
        chat_id: 聊天ID
        start_time: 开始时间戳
        end_time: 结束时间戳
        limit: 限制返回的消息数量，0为不限制
        limit_mode: 当limit>0时生效，'earliest'表示获取最早的记录，'latest'表示获取最新的记录

    Returns:
        消息列表
    """
    return get_raw_msg_by_timestamp_with_chat(chat_id, start_time, end_time, limit, limit_mode)


def get_messages_by_time_in_chat_inclusive(
    chat_id: str, start_time: float, end_time: float, limit: int = 0, limit_mode: str = "latest"
) -> List[Dict[str, Any]]:
    """
    获取指定聊天中指定时间范围内的消息（包含边界）

    Args:
        chat_id: 聊天ID
        start_time: 开始时间戳（包含）
        end_time: 结束时间戳（包含）
        limit: 限制返回的消息数量，0为不限制
        limit_mode: 当limit>0时生效，'earliest'表示获取最早的记录，'latest'表示获取最新的记录

    Returns:
        消息列表
    """
    return get_raw_msg_by_timestamp_with_chat_inclusive(chat_id, start_time, end_time, limit, limit_mode)


def get_messages_by_time_in_chat_for_users(
    chat_id: str,
    start_time: float,
    end_time: float,
    person_ids: list,
    limit: int = 0,
    limit_mode: str = "latest",
) -> List[Dict[str, Any]]:
    """
    获取指定聊天中指定用户在指定时间范围内的消息

    Args:
        chat_id: 聊天ID
        start_time: 开始时间戳
        end_time: 结束时间戳
        person_ids: 用户ID列表
        limit: 限制返回的消息数量，0为不限制
        limit_mode: 当limit>0时生效，'earliest'表示获取最早的记录，'latest'表示获取最新的记录

    Returns:
        消息列表
    """
    return get_raw_msg_by_timestamp_with_chat_users(chat_id, start_time, end_time, person_ids, limit, limit_mode)


def get_random_chat_messages(
    start_time: float, end_time: float, limit: int = 0, limit_mode: str = "latest"
) -> List[Dict[str, Any]]:
    """
    随机选择一个聊天，返回该聊天在指定时间范围内的消息

    Args:
        start_time: 开始时间戳
        end_time: 结束时间戳
        limit: 限制返回的消息数量，0为不限制
        limit_mode: 当limit>0时生效，'earliest'表示获取最早的记录，'latest'表示获取最新的记录

    Returns:
        消息列表
    """
    return get_raw_msg_by_timestamp_random(start_time, end_time, limit, limit_mode)


def get_messages_by_time_for_users(
    start_time: float, end_time: float, person_ids: list, limit: int = 0, limit_mode: str = "latest"
) -> List[Dict[str, Any]]:
    """
    获取指定用户在所有聊天中指定时间范围内的消息

    Args:
        start_time: 开始时间戳
        end_time: 结束时间戳
        person_ids: 用户ID列表
        limit: 限制返回的消息数量，0为不限制
        limit_mode: 当limit>0时生效，'earliest'表示获取最早的记录，'latest'表示获取最新的记录

    Returns:
        消息列表
    """
    return get_raw_msg_by_timestamp_with_users(start_time, end_time, person_ids, limit, limit_mode)


def get_messages_before_time(timestamp: float, limit: int = 0) -> List[Dict[str, Any]]:
    """
    获取指定时间戳之前的消息

    Args:
        timestamp: 时间戳
        limit: 限制返回的消息数量，0为不限制

    Returns:
        消息列表
    """
    return get_raw_msg_before_timestamp(timestamp, limit)


def get_messages_before_time_in_chat(chat_id: str, timestamp: float, limit: int = 0) -> List[Dict[str, Any]]:
    """
    获取指定聊天中指定时间戳之前的消息

    Args:
        chat_id: 聊天ID
        timestamp: 时间戳
        limit: 限制返回的消息数量，0为不限制

    Returns:
        消息列表
    """
    return get_raw_msg_before_timestamp_with_chat(chat_id, timestamp, limit)


def get_messages_before_time_for_users(timestamp: float, person_ids: list, limit: int = 0) -> List[Dict[str, Any]]:
    """
    获取指定用户在指定时间戳之前的消息

    Args:
        timestamp: 时间戳
        person_ids: 用户ID列表
        limit: 限制返回的消息数量，0为不限制

    Returns:
        消息列表
    """
    return get_raw_msg_before_timestamp_with_users(timestamp, person_ids, limit)


def get_recent_messages(
    chat_id: str, hours: float = 24.0, limit: int = 100, limit_mode: str = "latest"
) -> List[Dict[str, Any]]:
    """
    获取指定聊天中最近一段时间的消息

    Args:
        chat_id: 聊天ID
        hours: 最近多少小时，默认24小时
        limit: 限制返回的消息数量，默认100条
        limit_mode: 当limit>0时生效，'earliest'表示获取最早的记录，'latest'表示获取最新的记录

    Returns:
        消息列表
    """
    now = time.time()
    start_time = now - hours * 3600
    return get_raw_msg_by_timestamp_with_chat(chat_id, start_time, now, limit, limit_mode)


# =============================================================================
# 消息计数API函数
# =============================================================================


def count_new_messages(chat_id: str, start_time: float = 0.0, end_time: Optional[float] = None) -> int:
    """
    计算指定聊天中从开始时间到结束时间的新消息数量

    Args:
        chat_id: 聊天ID
        start_time: 开始时间戳
        end_time: 结束时间戳，如果为None则使用当前时间

    Returns:
        新消息数量
    """
    return num_new_messages_since(chat_id, start_time, end_time)


def count_new_messages_for_users(chat_id: str, start_time: float, end_time: float, person_ids: list) -> int:
    """
    计算指定聊天中指定用户从开始时间到结束时间的新消息数量

    Args:
        chat_id: 聊天ID
        start_time: 开始时间戳
        end_time: 结束时间戳
        person_ids: 用户ID列表

    Returns:
        新消息数量
    """
    return num_new_messages_since_with_users(chat_id, start_time, end_time, person_ids)


# =============================================================================
# 消息格式化API函数
# =============================================================================


def build_readable_messages_to_str(
    messages: List[Dict[str, Any]],
    replace_bot_name: bool = True,
    merge_messages: bool = False,
    timestamp_mode: str = "relative",
    read_mark: float = 0.0,
    truncate: bool = False,
    show_actions: bool = False,
) -> str:
    """
    将消息列表构建成可读的字符串

    Args:
        messages: 消息列表
        replace_bot_name: 是否将机器人的名称替换为"你"
        merge_messages: 是否合并连续消息
        timestamp_mode: 时间戳显示模式，'relative'或'absolute'
        read_mark: 已读标记时间戳，用于分割已读和未读消息
        truncate: 是否截断长消息
        show_actions: 是否显示动作记录

    Returns:
        格式化后的可读字符串
    """
    return build_readable_messages(
        messages, replace_bot_name, merge_messages, timestamp_mode, read_mark, truncate, show_actions
    )


async def build_readable_messages_with_details(
    messages: List[Dict[str, Any]],
    replace_bot_name: bool = True,
    merge_messages: bool = False,
    timestamp_mode: str = "relative",
    truncate: bool = False,
) -> Tuple[str, List[Tuple[float, str, str]]]:
    """
    将消息列表构建成可读的字符串，并返回详细信息

    Args:
        messages: 消息列表
        replace_bot_name: 是否将机器人的名称替换为"你"
        merge_messages: 是否合并连续消息
        timestamp_mode: 时间戳显示模式，'relative'或'absolute'
        truncate: 是否截断长消息

    Returns:
        格式化后的可读字符串和详细信息元组列表(时间戳, 昵称, 内容)
    """
    return await build_readable_messages_with_list(messages, replace_bot_name, merge_messages, timestamp_mode, truncate)


async def get_person_ids_from_messages(messages: List[Dict[str, Any]]) -> List[str]:
    """
    从消息列表中提取不重复的用户ID列表

    Args:
        messages: 消息列表

    Returns:
        用户ID列表
    """
    return await get_person_id_list(messages)

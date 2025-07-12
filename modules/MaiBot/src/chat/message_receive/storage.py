import re
from typing import Union

# from ...common.database.database import db  # db is now Peewee's SqliteDatabase instance
from .message import MessageSending, MessageRecv
from .chat_stream import ChatStream
from ...common.database.database_model import Messages, RecalledMessages  # Import Peewee models
from src.common.logger import get_logger

logger = get_logger("message_storage")


class MessageStorage:
    @staticmethod
    async def store_message(message: Union[MessageSending, MessageRecv], chat_stream: ChatStream) -> None:
        """存储消息到数据库"""
        try:
            # 莫越权 救世啊
            pattern = r"<MainRule>.*?</MainRule>|<schedule>.*?</schedule>|<UserMessage>.*?</UserMessage>"

            # print(message)

            processed_plain_text = message.processed_plain_text

            # print(processed_plain_text)

            if processed_plain_text:
                filtered_processed_plain_text = re.sub(pattern, "", processed_plain_text, flags=re.DOTALL)
            else:
                filtered_processed_plain_text = ""

            if isinstance(message, MessageSending):
                display_message = message.display_message
                if display_message:
                    filtered_display_message = re.sub(pattern, "", display_message, flags=re.DOTALL)
                else:
                    filtered_display_message = ""

                reply_to = message.reply_to
            else:
                filtered_display_message = ""

                reply_to = ""

            chat_info_dict = chat_stream.to_dict()
            user_info_dict = message.message_info.user_info.to_dict()

            # message_id 现在是 TextField，直接使用字符串值
            msg_id = message.message_info.message_id

            # 安全地获取 group_info, 如果为 None 则视为空字典
            group_info_from_chat = chat_info_dict.get("group_info") or {}
            # 安全地获取 user_info, 如果为 None 则视为空字典 (以防万一)
            user_info_from_chat = chat_info_dict.get("user_info") or {}

            Messages.create(
                message_id=msg_id,
                time=float(message.message_info.time),
                chat_id=chat_stream.stream_id,
                # Flattened chat_info
                reply_to=reply_to,
                chat_info_stream_id=chat_info_dict.get("stream_id"),
                chat_info_platform=chat_info_dict.get("platform"),
                chat_info_user_platform=user_info_from_chat.get("platform"),
                chat_info_user_id=user_info_from_chat.get("user_id"),
                chat_info_user_nickname=user_info_from_chat.get("user_nickname"),
                chat_info_user_cardname=user_info_from_chat.get("user_cardname"),
                chat_info_group_platform=group_info_from_chat.get("platform"),
                chat_info_group_id=group_info_from_chat.get("group_id"),
                chat_info_group_name=group_info_from_chat.get("group_name"),
                chat_info_create_time=float(chat_info_dict.get("create_time", 0.0)),
                chat_info_last_active_time=float(chat_info_dict.get("last_active_time", 0.0)),
                # Flattened user_info (message sender)
                user_platform=user_info_dict.get("platform"),
                user_id=user_info_dict.get("user_id"),
                user_nickname=user_info_dict.get("user_nickname"),
                user_cardname=user_info_dict.get("user_cardname"),
                # Text content
                processed_plain_text=filtered_processed_plain_text,
                display_message=filtered_display_message,
                memorized_times=message.memorized_times,
            )
        except Exception:
            logger.exception("存储消息失败")

    @staticmethod
    async def store_recalled_message(message_id: str, time: str, chat_stream: ChatStream) -> None:
        """存储撤回消息到数据库"""
        # Table creation is handled by initialize_database in database_model.py
        try:
            RecalledMessages.create(
                message_id=message_id,
                time=float(time),  # Assuming time is a string representing a float timestamp
                stream_id=chat_stream.stream_id,
            )
        except Exception:
            logger.exception("存储撤回消息失败")

    @staticmethod
    async def remove_recalled_message(time: str) -> None:
        """删除撤回消息"""
        try:
            # Assuming input 'time' is a string timestamp that can be converted to float
            current_time_float = float(time)
            RecalledMessages.delete().where(RecalledMessages.time < (current_time_float - 300)).execute()
        except Exception:
            logger.exception("删除撤回消息失败")

    # 如果需要其他存储相关的函数，可以在这里添加
    @staticmethod
    async def update_message(
        message: MessageRecv,
    ) -> None:  # 用于实时更新数据库的自身发送消息ID，目前能处理text,reply,image和emoji
        """更新最新一条匹配消息的message_id"""
        try:
            if message.message_segment.type == "notify":
                mmc_message_id = message.message_segment.data.get("echo")
                qq_message_id = message.message_segment.data.get("actual_id")
            else:
                logger.info(f"更新消息ID错误，seg类型为{message.message_segment.type}")
                return
            if not qq_message_id:
                logger.info("消息不存在message_id，无法更新")
                return
            # 查询最新一条匹配消息
            matched_message = (
                Messages.select().where((Messages.message_id == mmc_message_id)).order_by(Messages.time.desc()).first()
            )

            if matched_message:
                # 更新找到的消息记录
                Messages.update(message_id=qq_message_id).where(Messages.id == matched_message.id).execute()
                logger.info(f"更新消息ID成功: {matched_message.message_id} -> {qq_message_id}")
            else:
                logger.debug("未找到匹配的消息")

        except Exception as e:
            logger.error(f"更新消息ID失败: {e}")

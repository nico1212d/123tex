"""
禁言插件

提供智能禁言功能的群聊管理插件。

功能特性：
- 智能LLM判定：根据聊天内容智能判断是否需要禁言
- 灵活的时长管理：支持自定义禁言时长限制
- 模板化消息：支持自定义禁言提示消息
- 参数验证：完整的输入参数验证和错误处理
- 配置文件支持：所有设置可通过配置文件调整
- 权限管理：支持用户权限和群组权限控制

包含组件：
- 智能禁言Action - 基于LLM判断是否需要禁言（支持群组权限控制）
- 禁言命令Command - 手动执行禁言操作（支持用户权限控制）
"""

from typing import List, Tuple, Type, Optional
import random

# 导入新插件系统
from src.plugin_system.base.base_plugin import BasePlugin
from src.plugin_system.base.base_plugin import register_plugin
from src.plugin_system.base.base_action import BaseAction
from src.plugin_system.base.base_command import BaseCommand
from src.plugin_system.base.component_types import ComponentInfo, ActionActivationType, ChatMode
from src.plugin_system.base.config_types import ConfigField
from src.common.logger import get_logger

# 导入配置API（可选的简便方法）
from src.plugin_system.apis import person_api, generator_api

logger = get_logger("mute_plugin")


# ===== Action组件 =====


class MuteAction(BaseAction):
    """智能禁言Action - 基于LLM智能判断是否需要禁言"""

    # 激活设置
    focus_activation_type = ActionActivationType.LLM_JUDGE  # Focus模式使用LLM判定，确保谨慎
    normal_activation_type = ActionActivationType.KEYWORD  # Normal模式使用关键词激活，快速响应
    mode_enable = ChatMode.ALL
    parallel_action = False

    # 动作基本信息
    action_name = "mute"
    action_description = "智能禁言系统，基于LLM判断是否需要禁言"

    # 关键词设置（用于Normal模式）
    activation_keywords = ["禁言", "mute", "ban", "silence"]
    keyword_case_sensitive = False

    # LLM判定提示词（用于Focus模式）
    llm_judge_prompt = """
判定是否需要使用禁言动作的严格条件：

使用禁言的情况：
1. 用户发送明显违规内容（色情、暴力、政治敏感等）
2. 恶意刷屏或垃圾信息轰炸
3. 用户主动明确要求被禁言（"禁言我"等）
4. 严重违反群规的行为
5. 恶意攻击他人或群组管理

绝对不要使用的情况：
2. 情绪化表达但无恶意
3. 开玩笑或调侃，除非过分
4. 单纯的意见分歧或争论

"""

    # 动作参数定义
    action_parameters = {
        "target": "禁言对象，必填，输入你要禁言的对象的名字，请仔细思考不要弄错禁言对象",
        "duration": "禁言时长，必填，输入你要禁言的时长（秒），单位为秒，必须为数字",
        "reason": "禁言理由，可选",
    }

    # 动作使用场景
    action_require = [
        "当有人违反了公序良俗的内容",
        "当有人刷屏时使用",
        "当有人发了擦边，或者色情内容时使用",
        "当有人要求禁言自己时使用",
        "如果某人已经被禁言了，就不要再次禁言了，除非你想追加时间！！",
    ]

    # 关联类型
    associated_types = ["text", "command"]

    def _check_group_permission(self) -> Tuple[bool, Optional[str]]:
        """检查当前群是否有禁言动作权限

        Returns:
            Tuple[bool, Optional[str]]: (是否有权限, 错误信息)
        """
        # 如果不是群聊，直接返回False
        if not self.is_group:
            return False, "禁言动作只能在群聊中使用"

        # 获取权限配置
        allowed_groups = self.get_config("permissions.allowed_groups", [])

        # 如果配置为空，表示不启用权限控制
        if not allowed_groups:
            logger.info(f"{self.log_prefix} 群组权限未配置，允许所有群使用禁言动作")
            return True, None

        # 检查当前群是否在允许列表中
        current_group_key = f"{self.platform}:{self.group_id}"
        for allowed_group in allowed_groups:
            if allowed_group == current_group_key:
                logger.info(f"{self.log_prefix} 群组 {current_group_key} 有禁言动作权限")
                return True, None

        logger.warning(f"{self.log_prefix} 群组 {current_group_key} 没有禁言动作权限")
        return False, "当前群组没有使用禁言动作的权限"

    async def execute(self) -> Tuple[bool, Optional[str]]:
        """执行智能禁言判定"""
        logger.info(f"{self.log_prefix} 执行智能禁言动作")

        # 首先检查群组权限
        has_permission, permission_error = self._check_group_permission()

        # 获取参数
        target = self.action_data.get("target")
        duration = self.action_data.get("duration")
        reason = self.action_data.get("reason", "违反群规")

        # 参数验证
        if not target:
            error_msg = "禁言目标不能为空"
            logger.error(f"{self.log_prefix} {error_msg}")
            await self.send_text("没有指定禁言对象呢~")
            return False, error_msg

        if not duration:
            error_msg = "禁言时长不能为空"
            logger.error(f"{self.log_prefix} {error_msg}")
            await self.send_text("没有指定禁言时长呢~")
            return False, error_msg

        # 获取时长限制配置
        min_duration = self.get_config("mute.min_duration", 60)
        max_duration = self.get_config("mute.max_duration", 2592000)

        # 验证时长格式并转换
        try:
            duration_int = int(duration)
            if duration_int <= 0:
                error_msg = "禁言时长必须大于0"
                logger.error(f"{self.log_prefix} {error_msg}")
                await self.send_text("禁言时长必须是正数哦~")
                return False, error_msg

            # 限制禁言时长范围
            if duration_int < min_duration:
                duration_int = min_duration
                logger.info(f"{self.log_prefix} 禁言时长过短，调整为{min_duration}秒")
            elif duration_int > max_duration:
                duration_int = max_duration
                logger.info(f"{self.log_prefix} 禁言时长过长，调整为{max_duration}秒")

        except (ValueError, TypeError):
            error_msg = f"禁言时长格式无效: {duration}"
            logger.error(f"{self.log_prefix} {error_msg}")
            # await self.send_text("禁言时长必须是数字哦~")
            return False, error_msg

        # 获取用户ID
        person_id = person_api.get_person_id_by_name(target)
        user_id = await person_api.get_person_value(person_id, "user_id")
        if not user_id:
            error_msg = f"未找到用户 {target} 的ID"
            await self.send_text(f"找不到 {target} 这个人呢~")
            logger.error(f"{self.log_prefix} {error_msg}")
            return False, error_msg

        # 格式化时长显示
        enable_formatting = self.get_config("mute.enable_duration_formatting", True)
        time_str = self._format_duration(duration_int) if enable_formatting else f"{duration_int}秒"

        # 获取模板化消息
        message = self._get_template_message(target, time_str, reason)

        if not has_permission:
            logger.warning(f"{self.log_prefix} 权限检查失败: {permission_error}")
            result_status, result_message = await generator_api.rewrite_reply(
                chat_stream=self.chat_stream,
                reply_data={
                    "raw_reply": "我想禁言{target}，但是我没有权限",
                    "reason": "表达自己没有在这个群禁言的能力",
                },
            )

            if result_status:
                for reply_seg in result_message:
                    data = reply_seg[1]
                    await self.send_text(data)

            await self.store_action_info(
                action_build_into_prompt=True,
                action_prompt_display=f"尝试禁言了用户 {target}，但是没有权限，无法禁言",
                action_done=True,
            )

            # 不发送错误消息，静默拒绝
            return False, permission_error

        result_status, result_message = await generator_api.rewrite_reply(
            chat_stream=self.chat_stream,
            reply_data={
                "raw_reply": message,
                "reason": reason,
            },
        )

        if result_status:
            for reply_seg in result_message:
                data = reply_seg[1]
                await self.send_text(data)

        # 发送群聊禁言命令
        success = await self.send_command(
            command_name="GROUP_BAN", args={"qq_id": str(user_id), "duration": str(duration_int)}, storage_message=False
        )

        if success:
            logger.info(f"{self.log_prefix} 成功发送禁言命令，用户 {target}({user_id})，时长 {duration_int} 秒")
            # 存储动作信息
            await self.store_action_info(
                action_build_into_prompt=True,
                action_prompt_display=f"尝试禁言了用户 {target}，时长 {time_str}，原因：{reason}",
                action_done=True,
            )
            return True, f"成功禁言 {target}，时长 {time_str}"
        else:
            error_msg = "发送禁言命令失败"
            logger.error(f"{self.log_prefix} {error_msg}")

            await self.send_text("执行禁言动作失败")
            return False, error_msg

    def _get_template_message(self, target: str, duration_str: str, reason: str) -> str:
        """获取模板化的禁言消息"""
        templates = self.get_config("mute.templates")

        template = random.choice(templates)
        return template.format(target=target, duration=duration_str, reason=reason)

    def _format_duration(self, seconds: int) -> str:
        """将秒数格式化为可读的时间字符串"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            if remaining_seconds > 0:
                return f"{minutes}分{remaining_seconds}秒"
            else:
                return f"{minutes}分钟"
        elif seconds < 86400:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            if remaining_minutes > 0:
                return f"{hours}小时{remaining_minutes}分钟"
            else:
                return f"{hours}小时"
        else:
            days = seconds // 86400
            remaining_hours = (seconds % 86400) // 3600
            if remaining_hours > 0:
                return f"{days}天{remaining_hours}小时"
            else:
                return f"{days}天"


# ===== Command组件 =====


class MuteCommand(BaseCommand):
    """禁言命令 - 手动执行禁言操作"""

    # Command基本信息
    command_name = "mute_command"
    command_description = "禁言命令，手动执行禁言操作"

    command_pattern = r"^/mute\s+(?P<target>\S+)\s+(?P<duration>\d+)(?:\s+(?P<reason>.+))?$"
    command_help = "禁言指定用户，用法：/mute <用户名> <时长(秒)> [理由]"
    command_examples = ["/mute 用户名 300", "/mute 张三 600 刷屏", "/mute @某人 1800 违规内容"]
    intercept_message = True  # 拦截消息处理

    def _check_user_permission(self) -> Tuple[bool, Optional[str]]:
        """检查当前用户是否有禁言命令权限

        Returns:
            Tuple[bool, Optional[str]]: (是否有权限, 错误信息)
        """
        # 获取当前用户信息
        chat_stream = self.message.chat_stream
        if not chat_stream:
            return False, "无法获取聊天流信息"

        current_platform = chat_stream.platform
        current_user_id = str(chat_stream.user_info.user_id)

        # 获取权限配置
        allowed_users = self.get_config("permissions.allowed_users", [])

        # 如果配置为空，表示不启用权限控制
        if not allowed_users:
            logger.info(f"{self.log_prefix} 用户权限未配置，允许所有用户使用禁言命令")
            return True, None

        # 检查当前用户是否在允许列表中
        current_user_key = f"{current_platform}:{current_user_id}"
        for allowed_user in allowed_users:
            if allowed_user == current_user_key:
                logger.info(f"{self.log_prefix} 用户 {current_user_key} 有禁言命令权限")
                return True, None

        logger.warning(f"{self.log_prefix} 用户 {current_user_key} 没有禁言命令权限")
        return False, "你没有使用禁言命令的权限"

    async def execute(self) -> Tuple[bool, Optional[str]]:
        """执行禁言命令"""
        try:
            # 首先检查用户权限
            has_permission, permission_error = self._check_user_permission()
            if not has_permission:
                logger.error(f"{self.log_prefix} 权限检查失败: {permission_error}")
                await self.send_text(f"❌ {permission_error}")
                return False, permission_error

            target = self.matched_groups.get("target")
            duration = self.matched_groups.get("duration")
            reason = self.matched_groups.get("reason", "管理员操作")

            if not all([target, duration]):
                await self.send_text("❌ 命令参数不完整，请检查格式")
                return False, "参数不完整"

            # 获取时长限制配置
            min_duration = self.get_config("mute.min_duration", 60)
            max_duration = self.get_config("mute.max_duration", 2592000)

            # 验证时长
            try:
                duration_int = int(duration)
                if duration_int <= 0:
                    await self.send_text("❌ 禁言时长必须大于0")
                    return False, "时长无效"

                # 限制禁言时长范围
                if duration_int < min_duration:
                    duration_int = min_duration
                    await self.send_text(f"⚠️ 禁言时长过短，调整为{min_duration}秒")
                elif duration_int > max_duration:
                    duration_int = max_duration
                    await self.send_text(f"⚠️ 禁言时长过长，调整为{max_duration}秒")

            except ValueError:
                await self.send_text("❌ 禁言时长必须是数字")
                return False, "时长格式错误"

            # 获取用户ID
            person_id = person_api.get_person_id_by_name(target)
            user_id = await person_api.get_person_value(person_id, "user_id")
            if not user_id or user_id == "unknown":
                error_msg = f"未找到用户 {target} 的ID，请输入person_name进行禁言"
                await self.send_text(f"❌ 找不到用户 {target} 的ID，请输入person_name进行禁言，而不是qq号或者昵称")
                logger.error(f"{self.log_prefix} {error_msg}")
                return False, error_msg

            # 格式化时长显示
            enable_formatting = self.get_config("mute.enable_duration_formatting", True)
            time_str = self._format_duration(duration_int) if enable_formatting else f"{duration_int}秒"

            logger.info(f"{self.log_prefix} 执行禁言命令: {target}({user_id}) -> {time_str}")

            # 发送群聊禁言命令
            success = await self.send_command(
                command_name="GROUP_BAN",
                args={"qq_id": str(user_id), "duration": str(duration_int)},
                display_message=f"禁言了 {target} {time_str}",
            )

            if success:
                # 获取并发送模板化消息
                message = self._get_template_message(target, time_str, reason)
                await self.send_text(message)

                logger.info(f"{self.log_prefix} 成功禁言 {target}({user_id})，时长 {duration_int} 秒")
                return True, f"成功禁言 {target}，时长 {time_str}"
            else:
                await self.send_text("❌ 发送禁言命令失败")
                return False, "发送禁言命令失败"

        except Exception as e:
            logger.error(f"{self.log_prefix} 禁言命令执行失败: {e}")
            await self.send_text(f"❌ 禁言命令错误: {str(e)}")
            return False, str(e)

    def _get_template_message(self, target: str, duration_str: str, reason: str) -> str:
        """获取模板化的禁言消息"""
        templates = self.get_config("mute.templates")

        template = random.choice(templates)
        return template.format(target=target, duration=duration_str, reason=reason)

    def _format_duration(self, seconds: int) -> str:
        """将秒数格式化为可读的时间字符串"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            if remaining_seconds > 0:
                return f"{minutes}分{remaining_seconds}秒"
            else:
                return f"{minutes}分钟"
        elif seconds < 86400:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            if remaining_minutes > 0:
                return f"{hours}小时{remaining_minutes}分钟"
            else:
                return f"{hours}小时"
        else:
            days = seconds // 86400
            remaining_hours = (seconds % 86400) // 3600
            if remaining_hours > 0:
                return f"{days}天{remaining_hours}小时"
            else:
                return f"{days}天"


# ===== 插件主类 =====


@register_plugin
class MutePlugin(BasePlugin):
    """禁言插件

    提供智能禁言功能：
    - 智能禁言Action：基于LLM判断是否需要禁言（支持群组权限控制）
    - 禁言命令Command：手动执行禁言操作（支持用户权限控制）
    """

    # 插件基本信息
    plugin_name = "mute_plugin"  # 内部标识符
    enable_plugin = True
    config_file_name = "config.toml"

    # 配置节描述
    config_section_descriptions = {
        "plugin": "插件基本信息配置",
        "components": "组件启用控制",
        "permissions": "权限管理配置",
        "mute": "核心禁言功能配置",
        "smart_mute": "智能禁言Action的专属配置",
        "mute_command": "禁言命令Command的专属配置",
        "logging": "日志记录相关配置",
    }

    # 配置Schema定义
    config_schema = {
        "plugin": {
            "enabled": ConfigField(type=bool, default=False, description="是否启用插件"),
            "config_version": ConfigField(type=str, default="0.0.2", description="配置文件版本"),
        },
        "components": {
            "enable_smart_mute": ConfigField(type=bool, default=True, description="是否启用智能禁言Action"),
            "enable_mute_command": ConfigField(
                type=bool, default=False, description="是否启用禁言命令Command（调试用）"
            ),
        },
        "permissions": {
            "allowed_users": ConfigField(
                type=list,
                default=[],
                description="允许使用禁言命令的用户列表，格式：['platform:user_id']，如['qq:123456789']。空列表表示不启用权限控制",
            ),
            "allowed_groups": ConfigField(
                type=list,
                default=[],
                description="允许使用禁言动作的群组列表，格式：['platform:group_id']，如['qq:987654321']。空列表表示不启用权限控制",
            ),
        },
        "mute": {
            "min_duration": ConfigField(type=int, default=60, description="最短禁言时长（秒）"),
            "max_duration": ConfigField(type=int, default=2592000, description="最长禁言时长（秒），默认30天"),
            "default_duration": ConfigField(type=int, default=300, description="默认禁言时长（秒），默认5分钟"),
            "enable_duration_formatting": ConfigField(
                type=bool, default=True, description="是否启用人性化的时长显示（如 '5分钟' 而非 '300秒'）"
            ),
            "log_mute_history": ConfigField(type=bool, default=True, description="是否记录禁言历史（未来功能）"),
            "templates": ConfigField(
                type=list,
                default=[
                    "好的，禁言 {target} {duration}，理由：{reason}",
                    "收到，对 {target} 执行禁言 {duration}，因为{reason}",
                    "明白了，禁言 {target} {duration}，原因是{reason}",
                    "哇哈哈哈哈哈，已禁言 {target} {duration}，理由：{reason}",
                    "哎呦我去，对 {target} 执行禁言 {duration}，因为{reason}",
                    "{target}，你完蛋了，我要禁言你 {duration} 秒，原因：{reason}",
                ],
                description="成功禁言后发送的随机消息模板",
            ),
            "error_messages": ConfigField(
                type=list,
                default=[
                    "没有指定禁言对象呢~",
                    "没有指定禁言时长呢~",
                    "禁言时长必须是正数哦~",
                    "禁言时长必须是数字哦~",
                    "找不到 {target} 这个人呢~",
                    "查找用户信息时出现问题~",
                ],
                description="执行禁言过程中发生错误时发送的随机消息模板",
            ),
        },
        "smart_mute": {
            "strict_mode": ConfigField(type=bool, default=True, description="LLM判定的严格模式"),
            "keyword_sensitivity": ConfigField(
                type=str, default="normal", description="关键词激活的敏感度", choices=["low", "normal", "high"]
            ),
            "allow_parallel": ConfigField(type=bool, default=False, description="是否允许并行执行（暂未启用）"),
        },
        "mute_command": {
            "max_batch_size": ConfigField(type=int, default=5, description="最大批量禁言数量（未来功能）"),
            "cooldown_seconds": ConfigField(type=int, default=3, description="命令冷却时间（秒）"),
        },
        "logging": {
            "level": ConfigField(
                type=str, default="INFO", description="日志记录级别", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
            ),
            "prefix": ConfigField(type=str, default="[MutePlugin]", description="日志记录前缀"),
            "include_user_info": ConfigField(type=bool, default=True, description="日志中是否包含用户信息"),
            "include_duration_info": ConfigField(type=bool, default=True, description="日志中是否包含禁言时长信息"),
        },
    }

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        """返回插件包含的组件列表"""

        # 从配置获取组件启用状态
        enable_smart_mute = self.get_config("components.enable_smart_mute", True)
        enable_mute_command = self.get_config("components.enable_mute_command", True)

        components = []

        # 添加智能禁言Action
        if enable_smart_mute:
            components.append((MuteAction.get_action_info(), MuteAction))

        # 添加禁言命令Command
        if enable_mute_command:
            components.append((MuteCommand.get_command_info(), MuteCommand))

        return components

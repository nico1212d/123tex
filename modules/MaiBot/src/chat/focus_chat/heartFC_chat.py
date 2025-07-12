import asyncio
import contextlib
import time
import traceback
from collections import deque
from typing import List, Optional, Dict, Any, Deque, Callable, Awaitable
from src.chat.message_receive.chat_stream import get_chat_manager
from rich.traceback import install
from src.chat.utils.prompt_builder import global_prompt_manager
from src.common.logger import get_logger
from src.chat.utils.timer_calculator import Timer
from src.chat.heart_flow.observation.observation import Observation
from src.chat.focus_chat.heartFC_Cycleinfo import CycleDetail
from src.chat.focus_chat.info.info_base import InfoBase
from src.chat.focus_chat.info_processors.chattinginfo_processor import ChattingInfoProcessor
from src.chat.focus_chat.info_processors.working_memory_processor import WorkingMemoryProcessor
from src.chat.heart_flow.observation.hfcloop_observation import HFCloopObservation
from src.chat.heart_flow.observation.working_observation import WorkingMemoryObservation
from src.chat.heart_flow.observation.chatting_observation import ChattingObservation
from src.chat.heart_flow.observation.actions_observation import ActionObservation

from src.chat.focus_chat.memory_activator import MemoryActivator
from src.chat.focus_chat.info_processors.base_processor import BaseProcessor
from src.chat.focus_chat.planners.planner_factory import PlannerFactory
from src.chat.focus_chat.planners.modify_actions import ActionModifier
from src.chat.focus_chat.planners.action_manager import ActionManager
from src.config.config import global_config
from src.chat.focus_chat.hfc_performance_logger import HFCPerformanceLogger
from src.chat.focus_chat.hfc_version_manager import get_hfc_version
from src.person_info.relationship_builder_manager import relationship_builder_manager


install(extra_lines=3)

# 注释：原来的动作修改超时常量已移除，因为改为顺序执行

# 定义观察器映射：键是观察器名称，值是 (观察器类, 初始化参数)
OBSERVATION_CLASSES = {
    "ChattingObservation": (ChattingObservation, "chat_id"),
    "WorkingMemoryObservation": (WorkingMemoryObservation, "observe_id"),
    "HFCloopObservation": (HFCloopObservation, "observe_id"),
}

# 定义处理器映射：键是处理器名称，值是 (处理器类, 可选的配置键名)
PROCESSOR_CLASSES = {
    "ChattingInfoProcessor": (ChattingInfoProcessor, None),
    "WorkingMemoryProcessor": (WorkingMemoryProcessor, "working_memory_processor"),
}

logger = get_logger("hfc")  # Logger Name Changed


async def _handle_cycle_delay(action_taken_this_cycle: bool, cycle_start_time: float, log_prefix: str):
    """处理循环延迟"""
    cycle_duration = time.monotonic() - cycle_start_time

    try:
        sleep_duration = 0.0
        if not action_taken_this_cycle and cycle_duration < 1:
            sleep_duration = 1 - cycle_duration
        elif cycle_duration < 0.2:
            sleep_duration = 0.2

        if sleep_duration > 0:
            await asyncio.sleep(sleep_duration)

    except asyncio.CancelledError:
        logger.info(f"{log_prefix} Sleep interrupted, loop likely cancelling.")
        raise


class HeartFChatting:
    """
    管理一个连续的Focus Chat循环
    用于在特定聊天流中生成回复。
    其生命周期现在由其关联的 SubHeartflow 的 FOCUSED 状态控制。
    """

    def __init__(
        self,
        chat_id: str,
        on_stop_focus_chat: Optional[Callable[[], Awaitable[None]]] = None,
        performance_version: str = None,
    ):
        """
        HeartFChatting 初始化函数

        参数:
            chat_id: 聊天流唯一标识符(如stream_id)
            on_stop_focus_chat: 当收到stop_focus_chat命令时调用的回调函数
            performance_version: 性能记录版本号，用于区分不同启动版本
        """
        # 基础属性
        self.stream_id: str = chat_id  # 聊天流ID
        self.chat_stream = get_chat_manager().get_stream(self.stream_id)
        self.log_prefix = f"[{get_chat_manager().get_stream_name(self.stream_id) or self.stream_id}]"

        self.memory_activator = MemoryActivator()

        self.relationship_builder = relationship_builder_manager.get_or_create_builder(self.stream_id)

        # 新增：消息计数器和疲惫阈值
        self._message_count = 0  # 发送的消息计数
        # 基于exit_focus_threshold动态计算疲惫阈值
        # 基础值30条，通过exit_focus_threshold调节：threshold越小，越容易疲惫
        self._message_threshold = max(10, int(30 * global_config.chat.exit_focus_threshold))
        self._fatigue_triggered = False  # 是否已触发疲惫退出

        # 初始化观察器
        self.observations: List[Observation] = []
        self._register_observations()

        # 根据配置文件和默认规则确定启用的处理器
        self.enabled_processor_names = ["ChattingInfoProcessor"]
        if global_config.focus_chat.working_memory_processor:
            self.enabled_processor_names.append("WorkingMemoryProcessor")

        self.processors: List[BaseProcessor] = []
        self._register_default_processors()

        self.action_manager = ActionManager()
        self.action_planner = PlannerFactory.create_planner(
            log_prefix=self.log_prefix, action_manager=self.action_manager
        )
        self.action_modifier = ActionModifier(action_manager=self.action_manager)
        self.action_observation = ActionObservation(observe_id=self.stream_id)
        self.action_observation.set_action_manager(self.action_manager)

        self._processing_lock = asyncio.Lock()

        # 循环控制内部状态
        self._loop_active: bool = False  # 循环是否正在运行
        self._loop_task: Optional[asyncio.Task] = None  # 主循环任务

        # 添加循环信息管理相关的属性
        self._cycle_counter = 0
        self._cycle_history: Deque[CycleDetail] = deque(maxlen=10)  # 保留最近10个循环的信息
        self._current_cycle_detail: Optional[CycleDetail] = None
        self._shutting_down: bool = False  # 关闭标志位

        # 存储回调函数
        self.on_stop_focus_chat = on_stop_focus_chat

        # 初始化性能记录器
        # 如果没有指定版本号，则使用全局版本管理器的版本号
        actual_version = performance_version or get_hfc_version()
        self.performance_logger = HFCPerformanceLogger(chat_id, actual_version)

        logger.info(
            f"{self.log_prefix} HeartFChatting 初始化完成，消息疲惫阈值: {self._message_threshold}条（基于exit_focus_threshold={global_config.chat.exit_focus_threshold}计算，仅在auto模式下生效）"
        )

    def _register_observations(self):
        """注册所有观察器"""
        self.observations = []  # 清空已有的

        for name, (observation_class, param_name) in OBSERVATION_CLASSES.items():
            try:
                # 检查是否需要跳过WorkingMemoryObservation
                if name == "WorkingMemoryObservation":
                    # 如果工作记忆处理器被禁用，则跳过WorkingMemoryObservation
                    if not global_config.focus_chat.working_memory_processor:
                        logger.debug(f"{self.log_prefix} 工作记忆处理器已禁用，跳过注册观察器 {name}")
                        continue

                # 根据参数名使用正确的参数
                kwargs = {param_name: self.stream_id}
                observation = observation_class(**kwargs)
                self.observations.append(observation)
                logger.debug(f"{self.log_prefix} 注册观察器 {name}")
            except Exception as e:
                logger.error(f"{self.log_prefix} 观察器 {name} 构造失败: {e}")

        if self.observations:
            logger.info(f"{self.log_prefix} 已注册观察器: {[o.__class__.__name__ for o in self.observations]}")
        else:
            logger.warning(f"{self.log_prefix} 没有注册任何观察器")

    def _register_default_processors(self):
        """根据 self.enabled_processor_names 注册信息处理器"""
        self.processors = []  # 清空已有的

        for name in self.enabled_processor_names:  # 'name' is "ChattingInfoProcessor", etc.
            processor_info = PROCESSOR_CLASSES.get(name)  # processor_info is (ProcessorClass, config_key)
            if processor_info:
                processor_actual_class = processor_info[0]  # 获取实际的类定义
                # 根据处理器类名判断构造参数
                if name == "ChattingInfoProcessor":
                    self.processors.append(processor_actual_class())
                elif name == "WorkingMemoryProcessor":
                    self.processors.append(processor_actual_class(subheartflow_id=self.stream_id))
                else:
                    try:
                        self.processors.append(processor_actual_class())  # 尝试无参构造
                        logger.debug(f"{self.log_prefix} 注册处理器 {name} (尝试无参构造).")
                    except TypeError:
                        logger.error(
                            f"{self.log_prefix} 处理器 {name} 构造失败。它可能需要参数（如 subheartflow_id）但未在注册逻辑中明确处理。"
                        )
            else:
                logger.warning(
                    f"{self.log_prefix} 在 PROCESSOR_CLASSES 中未找到名为 '{name}' 的处理器定义，将跳过注册。"
                )

        if self.processors:
            logger.info(f"{self.log_prefix} 已注册处理器: {[p.__class__.__name__ for p in self.processors]}")
        else:
            logger.warning(f"{self.log_prefix} 没有注册任何处理器。这可能是由于配置错误或所有处理器都被禁用了。")

    async def start(self):
        """检查是否需要启动主循环，如果未激活则启动。"""
        logger.debug(f"{self.log_prefix} 开始启动 HeartFChatting")

        # 如果循环已经激活，直接返回
        if self._loop_active:
            logger.debug(f"{self.log_prefix} HeartFChatting 已激活，无需重复启动")
            return

        try:
            # 重置消息计数器，开始新的focus会话
            self.reset_message_count()

            # 标记为活动状态，防止重复启动
            self._loop_active = True

            # 检查是否已有任务在运行（理论上不应该，因为 _loop_active=False）
            if self._loop_task and not self._loop_task.done():
                logger.warning(f"{self.log_prefix} 发现之前的循环任务仍在运行（不符合预期）。取消旧任务。")
                self._loop_task.cancel()
                try:
                    # 等待旧任务确实被取消
                    await asyncio.wait_for(self._loop_task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass  # 忽略取消或超时错误
                except Exception as e:
                    logger.warning(f"{self.log_prefix} 等待旧任务取消时出错: {e}")
                self._loop_task = None  # 清理旧任务引用

            logger.debug(f"{self.log_prefix} 创建新的 HeartFChatting 主循环任务")
            self._loop_task = asyncio.create_task(self._run_focus_chat())
            self._loop_task.add_done_callback(self._handle_loop_completion)
            logger.debug(f"{self.log_prefix} HeartFChatting 启动完成")

        except Exception as e:
            # 启动失败时重置状态
            self._loop_active = False
            self._loop_task = None
            logger.error(f"{self.log_prefix} HeartFChatting 启动失败: {e}")
            raise

    def _handle_loop_completion(self, task: asyncio.Task):
        """当 _hfc_loop 任务完成时执行的回调。"""
        try:
            exception = task.exception()
            if exception:
                logger.error(f"{self.log_prefix} HeartFChatting: 脱离了聊天(异常): {exception}")
                logger.error(traceback.format_exc())  # Log full traceback for exceptions
            else:
                logger.info(f"{self.log_prefix} HeartFChatting: 脱离了聊天 (外部停止)")
        except asyncio.CancelledError:
            logger.info(f"{self.log_prefix} HeartFChatting: 脱离了聊天(任务取消)")
        finally:
            self._loop_active = False
            self._loop_task = None
            if self._processing_lock.locked():
                logger.warning(f"{self.log_prefix} HeartFChatting: 处理锁在循环结束时仍被锁定，强制释放。")
                self._processing_lock.release()

    async def _run_focus_chat(self):
        """主循环，持续进行计划并可能回复消息，直到被外部取消。"""
        try:
            while True:  # 主循环
                logger.debug(f"{self.log_prefix} 开始第{self._cycle_counter}次循环")

                # 检查关闭标志
                if self._shutting_down:
                    logger.info(f"{self.log_prefix} 检测到关闭标志，退出 Focus Chat 循环。")
                    break

                # 创建新的循环信息
                self._cycle_counter += 1
                self._current_cycle_detail = CycleDetail(self._cycle_counter)
                self._current_cycle_detail.prefix = self.log_prefix

                # 初始化周期状态
                cycle_timers = {}
                loop_cycle_start_time = time.monotonic()

                # 执行规划和处理阶段
                try:
                    async with self._get_cycle_context():
                        thinking_id = "tid" + str(round(time.time(), 2))
                        self._current_cycle_detail.set_thinking_id(thinking_id)

                        # 使用异步上下文管理器处理消息
                        try:
                            async with global_prompt_manager.async_message_scope(
                                self.chat_stream.context.get_template_name()
                            ):
                                # 在上下文内部检查关闭状态
                                if self._shutting_down:
                                    logger.info(f"{self.log_prefix} 在处理上下文中检测到关闭信号，退出")
                                    break

                                logger.debug(f"模板 {self.chat_stream.context.get_template_name()}")
                                loop_info = await self._observe_process_plan_action_loop(cycle_timers, thinking_id)

                                if loop_info["loop_action_info"]["command"] == "stop_focus_chat":
                                    logger.info(f"{self.log_prefix} 麦麦决定停止专注聊天")
                                    # 如果设置了回调函数，则调用它
                                    if self.on_stop_focus_chat:
                                        try:
                                            await self.on_stop_focus_chat()
                                            logger.info(f"{self.log_prefix} 成功调用回调函数处理停止专注聊天")
                                        except Exception as e:
                                            logger.error(f"{self.log_prefix} 调用停止专注聊天回调函数时出错: {e}")
                                            logger.error(traceback.format_exc())
                                    break

                        except asyncio.CancelledError:
                            logger.info(f"{self.log_prefix} 处理上下文时任务被取消")
                            break
                        except Exception as e:
                            logger.error(f"{self.log_prefix} 处理上下文时出错: {e}")
                            # 为当前循环设置错误状态，防止后续重复报错
                            error_loop_info = {
                                "loop_observation_info": {},
                                "loop_processor_info": {},
                                "loop_plan_info": {
                                    "action_result": {
                                        "action_type": "error",
                                        "action_data": {},
                                    },
                                    "observed_messages": "",
                                },
                                "loop_action_info": {
                                    "action_taken": False,
                                    "reply_text": "",
                                    "command": "",
                                    "taken_time": time.time(),
                                },
                            }
                            self._current_cycle_detail.set_loop_info(error_loop_info)
                            self._current_cycle_detail.complete_cycle()

                            # 上下文处理失败，跳过当前循环
                            await asyncio.sleep(1)
                            continue

                        self._current_cycle_detail.set_loop_info(loop_info)

                        # 从observations列表中获取HFCloopObservation
                        hfcloop_observation = next(
                            (obs for obs in self.observations if isinstance(obs, HFCloopObservation)), None
                        )
                        if hfcloop_observation:
                            hfcloop_observation.add_loop_info(self._current_cycle_detail)
                        else:
                            logger.warning(f"{self.log_prefix} 未找到HFCloopObservation实例")

                        self._current_cycle_detail.timers = cycle_timers

                        # 防止循环过快消耗资源
                        await _handle_cycle_delay(
                            loop_info["loop_action_info"]["action_taken"], loop_cycle_start_time, self.log_prefix
                        )

                    # 完成当前循环并保存历史
                    self._current_cycle_detail.complete_cycle()
                    self._cycle_history.append(self._current_cycle_detail)

                    # 记录循环信息和计时器结果
                    timer_strings = []
                    for name, elapsed in cycle_timers.items():
                        formatted_time = f"{elapsed * 1000:.2f}毫秒" if elapsed < 1 else f"{elapsed:.2f}秒"
                        timer_strings.append(f"{name}: {formatted_time}")

                    # 新增：输出每个处理器的耗时
                    processor_time_costs = self._current_cycle_detail.loop_processor_info.get(
                        "processor_time_costs", {}
                    )
                    processor_time_strings = []
                    for pname, ptime in processor_time_costs.items():
                        formatted_ptime = f"{ptime * 1000:.2f}毫秒" if ptime < 1 else f"{ptime:.2f}秒"
                        processor_time_strings.append(f"{pname}: {formatted_ptime}")
                    processor_time_log = (
                        ("\n前处理器耗时: " + "; ".join(processor_time_strings)) if processor_time_strings else ""
                    )

                    logger.info(
                        f"{self.log_prefix} 第{self._current_cycle_detail.cycle_id}次思考,"
                        f"耗时: {self._current_cycle_detail.end_time - self._current_cycle_detail.start_time:.1f}秒, "
                        f"动作: {self._current_cycle_detail.loop_plan_info.get('action_result', {}).get('action_type', '未知动作')}"
                        + (f"\n详情: {'; '.join(timer_strings)}" if timer_strings else "")
                        + processor_time_log
                    )

                    # 记录性能数据
                    try:
                        action_result = self._current_cycle_detail.loop_plan_info.get("action_result", {})
                        cycle_performance_data = {
                            "cycle_id": self._current_cycle_detail.cycle_id,
                            "action_type": action_result.get("action_type", "unknown"),
                            "total_time": self._current_cycle_detail.end_time - self._current_cycle_detail.start_time,
                            "step_times": cycle_timers.copy(),
                            "processor_time_costs": processor_time_costs,  # 处理器时间
                            "reasoning": action_result.get("reasoning", ""),
                            "success": self._current_cycle_detail.loop_action_info.get("action_taken", False),
                        }
                        self.performance_logger.record_cycle(cycle_performance_data)
                    except Exception as perf_e:
                        logger.warning(f"{self.log_prefix} 记录性能数据失败: {perf_e}")

                    await asyncio.sleep(global_config.focus_chat.think_interval)

                except asyncio.CancelledError:
                    logger.info(f"{self.log_prefix} 循环处理时任务被取消")
                    break
                except Exception as e:
                    logger.error(f"{self.log_prefix} 循环处理时出错: {e}")
                    logger.error(traceback.format_exc())

                    # 如果_current_cycle_detail存在但未完成，为其设置错误状态
                    if self._current_cycle_detail and not hasattr(self._current_cycle_detail, "end_time"):
                        error_loop_info = {
                            "loop_observation_info": {},
                            "loop_processor_info": {},
                            "loop_plan_info": {
                                "action_result": {
                                    "action_type": "error",
                                    "action_data": {},
                                    "reasoning": f"循环处理失败: {e}",
                                },
                                "observed_messages": "",
                            },
                            "loop_action_info": {
                                "action_taken": False,
                                "reply_text": "",
                                "command": "",
                                "taken_time": time.time(),
                            },
                        }
                        try:
                            self._current_cycle_detail.set_loop_info(error_loop_info)
                            self._current_cycle_detail.complete_cycle()
                        except Exception as inner_e:
                            logger.error(f"{self.log_prefix} 设置错误状态时出错: {inner_e}")

                    await asyncio.sleep(1)  # 出错后等待一秒再继续

        except asyncio.CancelledError:
            # 设置了关闭标志位后被取消是正常流程
            if not self._shutting_down:
                logger.warning(f"{self.log_prefix} 麦麦Focus聊天模式意外被取消")
            else:
                logger.info(f"{self.log_prefix} 麦麦已离开Focus聊天模式")
        except Exception as e:
            logger.error(f"{self.log_prefix} 麦麦Focus聊天模式意外错误: {e}")
            print(traceback.format_exc())

    @contextlib.asynccontextmanager
    async def _get_cycle_context(self):
        """
        循环周期的上下文管理器

        用于确保资源的正确获取和释放：
        1. 获取处理锁
        2. 执行操作
        3. 释放锁
        """
        acquired = False
        try:
            await self._processing_lock.acquire()
            acquired = True
            yield acquired
        finally:
            if acquired and self._processing_lock.locked():
                self._processing_lock.release()

    async def _process_processors(self, observations: List[Observation]) -> tuple[List[InfoBase], Dict[str, float]]:
        # 记录并行任务开始时间
        parallel_start_time = time.time()
        logger.debug(f"{self.log_prefix} 开始信息处理器并行任务")

        processor_tasks = []
        task_to_name_map = {}
        processor_time_costs = {}  # 新增: 记录每个处理器耗时

        for processor in self.processors:
            processor_name = processor.__class__.log_prefix

            async def run_with_timeout(proc=processor):
                return await asyncio.wait_for(proc.process_info(observations=observations), 30)

            task = asyncio.create_task(run_with_timeout())

            processor_tasks.append(task)
            task_to_name_map[task] = processor_name
            logger.debug(f"{self.log_prefix} 启动处理器任务: {processor_name}")

        pending_tasks = set(processor_tasks)
        all_plan_info: List[InfoBase] = []

        while pending_tasks:
            done, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                processor_name = task_to_name_map[task]
                task_completed_time = time.time()
                duration_since_parallel_start = task_completed_time - parallel_start_time

                try:
                    result_list = await task
                    logger.info(f"{self.log_prefix} 处理器 {processor_name} 已完成!")
                    if result_list is not None:
                        all_plan_info.extend(result_list)
                    else:
                        logger.warning(f"{self.log_prefix} 处理器 {processor_name} 返回了 None")
                    # 记录耗时
                    processor_time_costs[processor_name] = duration_since_parallel_start
                except asyncio.TimeoutError:
                    logger.info(f"{self.log_prefix} 处理器 {processor_name} 超时（>30s），已跳过")
                    processor_time_costs[processor_name] = 30
                except Exception as e:
                    logger.error(
                        f"{self.log_prefix} 处理器 {processor_name} 执行失败，耗时 (自并行开始): {duration_since_parallel_start:.2f}秒. 错误: {e}",
                        exc_info=True,
                    )
                    traceback.print_exc()
                    processor_time_costs[processor_name] = duration_since_parallel_start

            if pending_tasks:
                current_progress_time = time.time()
                elapsed_for_log = current_progress_time - parallel_start_time
                pending_names_for_log = [task_to_name_map[t] for t in pending_tasks]
                logger.info(
                    f"{self.log_prefix} 信息处理已进行 {elapsed_for_log:.2f}秒，待完成任务: {', '.join(pending_names_for_log)}"
                )

        # 所有任务完成后的最终日志
        parallel_end_time = time.time()
        total_duration = parallel_end_time - parallel_start_time
        logger.info(f"{self.log_prefix} 所有处理器任务全部完成，总耗时: {total_duration:.2f}秒")
        # logger.debug(f"{self.log_prefix} 所有信息处理器处理后的信息: {all_plan_info}")

        return all_plan_info, processor_time_costs

    async def _observe_process_plan_action_loop(self, cycle_timers: dict, thinking_id: str) -> dict:
        try:
            loop_start_time = time.time()
            with Timer("观察", cycle_timers):
                # 执行所有观察器的观察
                for observation in self.observations:
                    await observation.observe()

                loop_observation_info = {
                    "observations": self.observations,
                }

            await self.relationship_builder.build_relation()

            # 顺序执行调整动作和处理器阶段
            # 第一步：动作修改
            with Timer("动作修改", cycle_timers):
                try:
                    # 调用完整的动作修改流程
                    await self.action_modifier.modify_actions(
                        observations=self.observations,
                    )

                    await self.action_observation.observe()
                    self.observations.append(self.action_observation)
                    logger.debug(f"{self.log_prefix} 动作修改完成")
                except Exception as e:
                    logger.error(f"{self.log_prefix} 动作修改失败: {e}")
                    # 继续执行，不中断流程

            # 第二步：信息处理器
            with Timer("信息处理器", cycle_timers):
                try:
                    all_plan_info, processor_time_costs = await self._process_processors(self.observations)
                except Exception as e:
                    logger.error(f"{self.log_prefix} 信息处理器失败: {e}")
                    # 设置默认值以继续执行
                    all_plan_info = []
                    processor_time_costs = {}

            loop_processor_info = {
                "all_plan_info": all_plan_info,
                "processor_time_costs": processor_time_costs,
            }

            logger.debug(f"{self.log_prefix} 并行阶段完成，准备进入规划器，plan_info数量: {len(all_plan_info)}")

            with Timer("规划器", cycle_timers):
                plan_result = await self.action_planner.plan(all_plan_info, self.observations, loop_start_time)

                loop_plan_info = {
                    "action_result": plan_result.get("action_result", {}),
                    "observed_messages": plan_result.get("observed_messages", ""),
                }

            action_type, action_data, reasoning = (
                plan_result.get("action_result", {}).get("action_type", "error"),
                plan_result.get("action_result", {}).get("action_data", {}),
                plan_result.get("action_result", {}).get("reasoning", "未提供理由"),
            )

            if action_type == "reply":
                action_str = "回复"
            elif action_type == "no_reply":
                action_str = "不回复"
            else:
                action_str = action_type

            logger.debug(f"{self.log_prefix} 麦麦想要：'{action_str}'")

            # 动作执行计时
            with Timer("动作执行", cycle_timers):
                success, reply_text, command = await self._handle_action(
                    action_type, reasoning, action_data, cycle_timers, thinking_id
                )

                loop_action_info = {
                    "action_taken": success,
                    "reply_text": reply_text,
                    "command": command,
                    "taken_time": time.time(),
                }

            loop_info = {
                "loop_observation_info": loop_observation_info,
                "loop_processor_info": loop_processor_info,
                "loop_plan_info": loop_plan_info,
                "loop_action_info": loop_action_info,
            }

            return loop_info

        except Exception as e:
            logger.error(f"{self.log_prefix} FOCUS聊天处理失败: {e}")
            logger.error(traceback.format_exc())
            return {
                "loop_observation_info": {},
                "loop_processor_info": {},
                "loop_plan_info": {
                    "action_result": {"action_type": "error", "action_data": {}, "reasoning": f"处理失败: {e}"},
                    "observed_messages": "",
                },
                "loop_action_info": {"action_taken": False, "reply_text": "", "command": "", "taken_time": time.time()},
            }

    async def _handle_action(
        self,
        action: str,
        reasoning: str,
        action_data: dict,
        cycle_timers: dict,
        thinking_id: str,
    ) -> tuple[bool, str, str]:
        """
        处理规划动作，使用动作工厂创建相应的动作处理器

        参数:
            action: 动作类型
            reasoning: 决策理由
            action_data: 动作数据，包含不同动作需要的参数
            cycle_timers: 计时器字典
            thinking_id: 思考ID

        返回:
            tuple[bool, str, str]: (是否执行了动作, 思考消息ID, 命令)
        """
        try:
            # 使用工厂创建动作处理器实例
            try:
                action_handler = self.action_manager.create_action(
                    action_name=action,
                    action_data=action_data,
                    reasoning=reasoning,
                    cycle_timers=cycle_timers,
                    thinking_id=thinking_id,
                    chat_stream=self.chat_stream,
                    log_prefix=self.log_prefix,
                    shutting_down=self._shutting_down,
                )
            except Exception as e:
                logger.error(f"{self.log_prefix} 创建动作处理器时出错: {e}")
                traceback.print_exc()
                return False, "", ""

            if not action_handler:
                logger.warning(f"{self.log_prefix} 未能创建动作处理器: {action}, 原因: {reasoning}")
                return False, "", ""

            # 处理动作并获取结果
            result = await action_handler.handle_action()
            if len(result) == 3:
                success, reply_text, command = result
            else:
                success, reply_text = result
                command = ""

            # 检查action_data中是否有系统命令，优先使用系统命令
            if "_system_command" in action_data:
                command = action_data["_system_command"]
                logger.debug(f"{self.log_prefix} 从action_data中获取系统命令: {command}")

            # 新增：消息计数和疲惫检查
            if action == "reply" and success:
                self._message_count += 1
                current_threshold = self._get_current_fatigue_threshold()
                logger.info(
                    f"{self.log_prefix} 已发送第 {self._message_count} 条消息（动态阈值: {current_threshold}, exit_focus_threshold: {global_config.chat.exit_focus_threshold}）"
                )

                # 检查是否达到疲惫阈值（只有在auto模式下才会自动退出）
                if (
                    global_config.chat.chat_mode == "auto"
                    and self._message_count >= current_threshold
                    and not self._fatigue_triggered
                ):
                    self._fatigue_triggered = True
                    logger.info(
                        f"{self.log_prefix} [auto模式] 已发送 {self._message_count} 条消息，达到疲惫阈值 {current_threshold}，麦麦感到疲惫了，准备退出专注聊天模式"
                    )
                    # 设置系统命令，在下次循环检查时触发退出
                    command = "stop_focus_chat"
                elif self._message_count >= current_threshold and global_config.chat.chat_mode != "auto":
                    logger.info(
                        f"{self.log_prefix} [非auto模式] 已发送 {self._message_count} 条消息，达到疲惫阈值 {current_threshold}，但非auto模式不会自动退出"
                    )

            logger.debug(f"{self.log_prefix} 麦麦执行了'{action}', 返回结果'{success}', '{reply_text}', '{command}'")

            return success, reply_text, command

        except Exception as e:
            logger.error(f"{self.log_prefix} 处理{action}时出错: {e}")
            traceback.print_exc()
            return False, "", ""

    def _get_current_fatigue_threshold(self) -> int:
        """动态获取当前的疲惫阈值，基于exit_focus_threshold配置

        Returns:
            int: 当前的疲惫阈值
        """
        return max(10, int(30 / global_config.chat.exit_focus_threshold))

    def get_message_count_info(self) -> dict:
        """获取消息计数信息

        Returns:
            dict: 包含消息计数信息的字典
        """
        current_threshold = self._get_current_fatigue_threshold()
        return {
            "current_count": self._message_count,
            "threshold": current_threshold,
            "fatigue_triggered": self._fatigue_triggered,
            "remaining": max(0, current_threshold - self._message_count),
        }

    def reset_message_count(self):
        """重置消息计数器（用于重新启动focus模式时）"""
        self._message_count = 0
        self._fatigue_triggered = False
        logger.info(f"{self.log_prefix} 消息计数器已重置")

    async def shutdown(self):
        """优雅关闭HeartFChatting实例，取消活动循环任务"""
        logger.info(f"{self.log_prefix} 正在关闭HeartFChatting...")
        self._shutting_down = True  # <-- 在开始关闭时设置标志位

        # 记录最终的消息统计
        if self._message_count > 0:
            logger.info(f"{self.log_prefix} 本次focus会话共发送了 {self._message_count} 条消息")
            if self._fatigue_triggered:
                logger.info(f"{self.log_prefix} 因疲惫而退出focus模式")

        # 取消循环任务
        if self._loop_task and not self._loop_task.done():
            logger.info(f"{self.log_prefix} 正在取消HeartFChatting循环任务")
            self._loop_task.cancel()
            try:
                await asyncio.wait_for(self._loop_task, timeout=1.0)
                logger.info(f"{self.log_prefix} HeartFChatting循环任务已取消")
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                logger.error(f"{self.log_prefix} 取消循环任务出错: {e}")
        else:
            logger.info(f"{self.log_prefix} 没有活动的HeartFChatting循环任务")

        # 清理状态
        self._loop_active = False
        self._loop_task = None
        if self._processing_lock.locked():
            self._processing_lock.release()
            logger.warning(f"{self.log_prefix} 已释放处理锁")

        # 完成性能统计
        try:
            self.performance_logger.finalize_session()
            logger.info(f"{self.log_prefix} 性能统计已完成")
        except Exception as e:
            logger.warning(f"{self.log_prefix} 完成性能统计时出错: {e}")

        # 重置消息计数器，为下次启动做准备
        self.reset_message_count()

        logger.info(f"{self.log_prefix} HeartFChatting关闭完成")

    def get_cycle_history(self, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取循环历史记录

        参数:
            last_n: 获取最近n个循环的信息，如果为None则获取所有历史记录

        返回:
            List[Dict[str, Any]]: 循环历史记录列表
        """
        history = list(self._cycle_history)
        if last_n is not None:
            history = history[-last_n:]
        return [cycle.to_dict() for cycle in history]

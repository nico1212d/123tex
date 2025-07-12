# 定义了来自外部世界的信息
# 外部世界可以是某个聊天 不同平台的聊天 也可以是任意媒体
from datetime import datetime
from src.common.logger import get_logger
from src.chat.focus_chat.working_memory.working_memory import WorkingMemory
from src.chat.focus_chat.working_memory.memory_item import MemoryItem
from typing import List
# Import the new utility function

logger = get_logger("observation")


# 所有观察的基类
class WorkingMemoryObservation:
    def __init__(self, observe_id):
        self.observe_info = ""
        self.observe_id = observe_id
        self.last_observe_time = datetime.now().timestamp()

        self.working_memory = WorkingMemory(chat_id=observe_id)

        self.retrieved_working_memory = []

    def get_observe_info(self):
        return self.working_memory

    def add_retrieved_working_memory(self, retrieved_working_memory: List[MemoryItem]):
        self.retrieved_working_memory.append(retrieved_working_memory)

    def get_retrieved_working_memory(self):
        return self.retrieved_working_memory

    async def observe(self):
        pass

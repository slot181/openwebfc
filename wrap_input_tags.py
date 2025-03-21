from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timedelta

class Filter:
    # 可选的配置选项
    class Valves(BaseModel):
        pass

    def __init__(self):
        # 初始化配置
        self.valves = self.Valves()

    # 处理用户输入的函数
    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # 遍历所有消息
        for message in body.get("messages", []):
            # 只处理用户角色的消息
            if message.get("role") == "user":
                # 获取当前UTC时间并转换为北京时间（UTC+8）
                current_time = datetime.now(timezone.utc)
                beijing_time = current_time.astimezone(timezone(timedelta(hours=8)))
                formatted_time = beijing_time.strftime("%Y-%m-%d %H:%M:%S")
                # 将用户消息添加时间戳并用<inputs>标签包裹
                message["content"] = f"[时间: {formatted_time}]\n<inputs>{message['content']}</inputs>"
        
        return body

    # 处理流式输出的函数 (0.5.17新功能)
    def stream(self, event: dict) -> dict:
        # 不修改流式输出
        return event

    # 处理模型最终输出的函数
    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # 不修改模型的回复
        return body

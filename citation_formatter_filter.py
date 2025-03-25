"""
title: 引用包装与索引清理器
author: Roo
description: 这个过滤器将AI搜索到的来源列表用反引号包裹起来，并过滤掉引用来源列表以外文本中的索引标签[]
version: 1.2.0
license: MIT
"""

from pydantic import BaseModel
from typing import Optional
import re

class Filter:
    """
    引用包装与索引清理器 - 将AI搜索到的来源列表用反引号包裹起来，并过滤掉引用来源列表以外文本中的索引标签[]
    """
    
    class Valves(BaseModel):
        """过滤器的配置选项"""
        pass
    
    def __init__(self):
        """初始化过滤器"""
        self.valves = self.Valves()
    
    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        输入预处理 - 在这个过滤器中不需要修改输入
        """
        return body
    
    def stream(self, event: dict) -> dict:
        """
        实时流处理 - 在这个过滤器中不需要修改流
        """
        return event
    
    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        输出后处理 - 将引用来源列表用反引号包裹起来，并过滤掉引用来源列表以外文本中的索引标签[]
        """
        # 检查消息列表是否存在
        if "messages" not in body:
            return body
        
        # 遍历所有消息
        for message in body["messages"]:
            # 只处理助手的消息
            if message.get("role") == "assistant" and "content" in message:
                content = message["content"]
                
                # 查找引用来源列表
                # 匹配任何以<details>开头并以</details>结尾的内容
                citation_pattern = r'(<details>.*?</details>)'
                
                # 使用正则表达式查找引用来源列表
                citation_matches = list(re.finditer(citation_pattern, content, re.DOTALL))
                
                # 如果找到了引用来源列表
                if citation_matches:
                    # 创建一个新的内容字符串
                    new_content = ""
                    last_end = 0
                    
                    # 处理每个引用来源列表及其前后的文本
                    for match in citation_matches:
                        # 获取当前匹配的起始和结束位置
                        start, end = match.span()
                        
                        # 处理引用来源列表前的文本（移除索引标签[]）
                        before_text = content[last_end:start]
                        # 使用正则表达式移除索引标签
                        # 匹配HTML格式的上标索引标签 <sup>[数字]</sup>
                        before_text = re.sub(r'<sup>\[\d+\]</sup>', '', before_text)
                        # 匹配纯文本格式的索引标签 [数字]
                        before_text = re.sub(r'\[\d+\]', '', before_text)
                        
                        # 添加处理后的文本到新内容
                        new_content += before_text
                        
                        # 获取引用来源列表
                        citation_list = match.group(1)
                        # 用反引号包裹引用来源列表
                        wrapped_citation = f"```\n{citation_list}\n```"
                        # 添加包裹后的引用来源列表到新内容
                        new_content += wrapped_citation
                        
                        # 更新上一个结束位置
                        last_end = end
                    
                    # 处理最后一个引用来源列表后的文本（如果有）
                    if last_end < len(content):
                        after_text = content[last_end:]
                        # 使用正则表达式移除索引标签
                        after_text = re.sub(r'<sup>\[\d+\]</sup>', '', after_text)
                        after_text = re.sub(r'\[\d+\]', '', after_text)
                        new_content += after_text
                    
                    # 更新消息内容
                    message["content"] = new_content
                else:
                    # 如果没有找到引用来源列表，只移除索引标签
                    content = re.sub(r'<sup>\[\d+\]</sup>', '', content)
                    content = re.sub(r'\[\d+\]', '', content)
                    message["content"] = content
        
        return body
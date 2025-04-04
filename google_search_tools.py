"""
title: 网络搜索服务
author: OpenWebUI
author_url: https://openwebui.com
description: 用于获取最新信息、新闻、数据、事实、游戏资讯、小说内容、影视作品、体育赛事、科技动态、产品评测、学术研究、旅游信息和时事热点的综合网络搜索服务
version: 1.3.0
license: MIT
requirements: requests, pydantic
"""

from typing import Callable, Any, List, Dict, Optional, Tuple
from pydantic import BaseModel, Field
import requests
import json
import asyncio
import re
from datetime import datetime


class Tools:
    # 定义常量
    DEFAULT_ENDPOINT_PATH = "v1beta/models/{model}:generateContent"

    class Valves(BaseModel):
        api_url: str = Field(
            "https://deno-arna-geminipool.deno.dev", description="Gemini API基础URL"
        )
        api_key: str = Field("", description="Gemini API密钥")
        model: str = Field("gemini-2.0-flash-exp", description="Gemini模型名称")

    def __init__(self):
        self.valves = self.Valves()
        # 禁用自动引用，使用自定义引用处理
        self.citation = False

    def _build_api_url(self) -> str:
        """构建完整的API URL"""
        endpoint_path = self.DEFAULT_ENDPOINT_PATH.format(model=self.valves.model)
        return f"{self.valves.api_url}/{endpoint_path}?key={self.valves.api_key}"

    async def _emit_status(
        self,
        __event_emitter__: Callable[[dict], Any],
        status: str,
        description: str,
        done: bool = False,
    ):
        """发送状态更新"""
        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "status": status,
                    "description": description,
                    "done": done,
                },
            }
        )

    async def _emit_citation(
        self,
        __event_emitter__: Callable[[dict], Any],
        title: str,
        url: str,
        content: str,
        index: int = None,
    ):
        """发送引用信息"""
        data = {
            "document": [content],
            "metadata": [
                {
                    "date_accessed": datetime.now().isoformat(),
                    "source": title,
                }
            ],
            "source": {"name": title, "url": url},
        }

        # 如果提供了索引，添加到数据中
        if index is not None:
            data["index"] = index

        await __event_emitter__({"type": "citation", "data": data})

    async def _emit_message(
        self, __event_emitter__: Callable[[dict], Any], content: str
    ):
        """发送消息更新"""
        await __event_emitter__(
            {
                "type": "message",
                "data": {"content": content},
            }
        )

    # 移除_extract_context方法，因为不再需要基于上下文优化搜索查询

    def _process_grounding_supports(
        self, text: str, supports: List[Dict], chunks: List[Dict]
    ) -> str:
        """处理引用支持，在文本中添加引用标记"""
        if not supports or not chunks:
            return text

        # 按照结束索引降序排序，以便从后向前处理，避免索引错位
        sorted_supports = sorted(
            supports, key=lambda x: x["segment"]["endIndex"], reverse=True
        )

        for support in sorted_supports:
            segment = support["segment"]
            start_idx = segment["startIndex"]
            end_idx = segment["endIndex"]

            # 获取引用的chunk索引
            chunk_indices = support["groundingChunkIndices"]
            if not chunk_indices:
                continue

            # 创建引用标记
            citations = []
            for idx in chunk_indices:
                if idx < len(chunks):
                    citations.append(f"<sup>[{idx+1}]</sup>")

            citation_str = "".join(citations)

            # 在文本中插入引用标记
            if end_idx <= len(text):
                text = text[:end_idx] + citation_str + text[end_idx:]

        return text

    async def get_realtime_information(
        self,
        query: str,
        __event_emitter__: Callable[[dict], Any]
    ) -> str:
        """
        执行网络搜索，获取网络上的最新信息

        :param query: 根据上下文和用户回复提取关键字查询
        :param __event_emitter__: 状态更新事件发射器
        :return: 搜索结果（JSON字符串格式）
        """
        # 直接使用用户提供的查询，不再基于上下文优化
        search_query = query

        # 显示正在搜索的状态
        await self._emit_status(__event_emitter__, "searching", f"正在搜索: {query}")

        try:
            # 构建API URL
            api_url = self._build_api_url()

            # 准备请求数据
            payload = {
                "contents": [
                    {"parts": [{"text": f"Search for: {search_query}"}], "role": "user"}
                ],
                "tools": [{"google_search": {}}],
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE",
                    },
                ],
            }

            # 发送请求
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            result = response.json()

            if result.get("candidates") and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                content = candidate["content"]["parts"][0]["text"]

                # 处理引用信息
                grounding_metadata = candidate.get("groundingMetadata", {})
                grounding_chunks = grounding_metadata.get("groundingChunks", [])
                grounding_supports = grounding_metadata.get("groundingSupports", [])

                # 在文本中添加引用标记
                if grounding_supports and grounding_chunks:
                    # 使用更可靠的方式添加引用标记
                    # 首先创建一个映射，记录每个chunk的索引号
                    chunk_to_index = {}
                    for i, chunk in enumerate(grounding_chunks):
                        chunk_to_index[i] = i  # 索引号从0开始

                    # 然后创建一个映射，记录每个文本段落应该使用哪些引用
                    text_to_citations = {}
                    for support in grounding_supports:
                        if "segment" in support and "text" in support["segment"]:
                            text = support["segment"]["text"]
                            chunk_indices = support.get("groundingChunkIndices", [])
                            if chunk_indices:
                                citations = []
                                for idx in chunk_indices:
                                    if idx < len(grounding_chunks):
                                        # 使用chunk_to_index确保索引号一致，使用Markdown格式
                                        citations.append(f"[{chunk_to_index[idx]}]")
                                if citations:
                                    text_to_citations[text] = " ".join(citations)

                    # 然后在content中查找这些文本段落，并添加引用标记
                    for text, citation in text_to_citations.items():
                        if text in content:
                            # 确保只替换完整的文本段落，避免部分匹配
                            content = content.replace(text, f"{text} {citation}")

                # 发送引用信息
                if grounding_chunks and grounding_supports:
                    # 创建引用来源列表（使用可折叠的HTML标签包裹）
                    citations_md = "\n<details>\n<summary>引用来源</summary>\n\n"

                    # 创建chunk索引到support文本的映射
                    chunk_to_supports = {}
                    for support in grounding_supports:
                        segment = support["segment"]
                        for chunk_idx in support["groundingChunkIndices"]:
                            if chunk_idx not in chunk_to_supports:
                                chunk_to_supports[chunk_idx] = []
                            # 使用segment中的text作为引用内容
                            if "text" in segment:
                                chunk_to_supports[chunk_idx].append(segment["text"])

                    # 为每个groundingChunk创建一个引用条目
                    for i, chunk in enumerate(grounding_chunks):
                        if "web" in chunk:
                            title = chunk["web"].get("title", "未知来源")
                            uri = chunk["web"].get("uri", "#")

                            # 获取与此chunk关联的文本内容
                            support_texts = chunk_to_supports.get(i, [])

                            # 创建Markdown格式的引用条目
                            citations_md += f"{i+1}. [{title}]({uri})\n"

                            if support_texts:
                                # 合并所有相关的支持文本
                                citation_content = "\n\n".join(support_texts)
                                # 添加引用内容（使用Markdown引用格式）
                                formatted_texts = []
                                for text in support_texts:
                                    # 将每个支持文本格式化为Markdown引用格式
                                    formatted_text = "\n   ".join(text.split("\n"))
                                    formatted_texts.append(f"   {formatted_text}")

                                citations_md += (
                                    "\n" + "\n\n".join(formatted_texts) + "\n\n"
                                )
                            else:
                                citation_content = f"引用来源 [{i+1}]: {title}"
                                citations_md += "\n"

                            # 为每个引用源发送citation事件，明确指定索引号
                            await self._emit_citation(
                                __event_emitter__,
                                title,
                                uri,
                                citation_content,
                                i + 1,  # 传递从1开始的索引
                            )

                    # 添加结束标记
                    citations_md += "\n</details>\n"

                    # 将引用信息添加到消息体的上下文中
                    await self._emit_message(__event_emitter__, f"\n\n{citations_md}")

                # 注意：移除了尝试将搜索信息添加到上下文的方法，因为这种方法不可行

                # 添加搜索完成状态更新
                await self._emit_status(
                    __event_emitter__, "completed", f"搜索完成: {query}", True
                )

                # 创建一个新的内容，包含谷歌搜索返回的文本和引用列表
                # 这样AI就能知道正确的索引号
                new_content = content

                # 如果有引用信息，添加引用列表到内容中
                if grounding_chunks and grounding_supports:
                    new_content += f"\n\n{citations_md}"

                # 修改原始响应中的内容，替换为我们创建的新内容
                if result.get("candidates") and len(result["candidates"]) > 0:
                    result["candidates"][0]["content"]["parts"][0]["text"] = new_content

                # 返回结果，包含修改后的响应以便AI可以访问完整信息
                return json.dumps(
                    {
                        "result": new_content,
                        "has_citations": bool(grounding_chunks),
                        "raw_response": result,
                    }
                )
            else:
                # 添加搜索完成状态更新（无结果）
                await self._emit_status(
                    __event_emitter__, "completed", f"搜索完成，但未获得有效结果", True
                )
                return json.dumps({"error": "No valid response from the API"})

        except Exception as e:
            error_msg = f"搜索错误: {str(e)}"

            # 添加搜索错误状态更新
            await self._emit_status(__event_emitter__, "error", error_msg, True)

            return json.dumps({"error": error_msg})

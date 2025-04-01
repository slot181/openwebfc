"""
title: 音乐助手
author: OpenWebUI
author_url: https://openwebui.com
description: 用于提供歌曲、专辑、艺术家及音乐相关信息的音乐搜索服务
required_open_webui_version: 0.4.0
requirements: requests
version: 1.1.0
licence: MIT
"""

import requests
import json
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Tools:
    class UserValves(BaseModel):
        show_lyrics: bool = Field(
            default=True, description="是否显示歌词"
        )
    
    def __init__(self):
        """初始化音乐搜索工具"""
        self.api_url = "https://api.lolimi.cn/API/wydg/"
        self.user_valves = self.UserValves()
        self.citation = False
    
    async def find_songs(self, query: str, __event_emitter__=None) -> str:
        """
        执行音乐搜索，获取相关音乐列表信息

        :param query: 从上下文和用户回复中提取歌曲名字查询
        """
        try:
            # 发送状态更新
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": f"正在搜索歌曲: {query}", "done": False},
                    }
                )
            
            # 构建API请求URL
            params = {"msg": query}
            response = requests.get(self.api_url, params=params)
            data = response.json()
            
            if data["code"] != 200:
                return f"搜索失败: {data.get('msg', '未知错误')}"
            
            # 构建搜索结果
            if not data.get("data"):
                return "未找到相关歌曲"
            
            # 通过事件发射器发送搜索结果标题
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "message",
                        "data": {"content": "\n<details>\n<summary>歌曲列表</summary>\n\n"},
                    }
                )
            
            # 为每首歌曲单独发送一个事件，使用简洁的列表形式
            for i, song in enumerate(data["data"]):
                song_info = f"{i+1}. **{song['name']}** - {song['singer']} (ID: {song['id']})"
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "message",
                            "data": {"content": f"{song_info}\n"},
                        }
                    )
            
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "message",
                        "data": {"content": "\n</details>\n"},
                    }
                )
            
            # 发送完成状态
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "搜索完成", "done": True},
                    }
                )

            # 返回一个结果字符串进行提示
            result = "搜索完成，已获取歌曲列表，请根据歌曲序号告诉我想听哪一首。"
            return result
        
        except Exception as e:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": f"发生错误: {str(e)}", "done": True},
                    }
                )
            return f"搜索过程中发生错误: {str(e)}"
    
    async def get_song_detail(self, query: str, song_number: int, __event_emitter__=None) -> str:
        """
        执行某首歌曲的搜索，获取相关歌曲的详细信息

        :param query: 从上下文和用户回复中提取歌曲名字查询
        :param song_number: 从音乐列表中获取歌曲序号查询
        """
        try:
            # 发送状态更新
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": f"正在获取歌曲: {query} (序号: {song_number})", "done": False},
                    }
                )
            
            # 构建API请求URL
            params = {"msg": query, "n": song_number}
            response = requests.get(self.api_url, params=params)
            data = response.json()
            
            if data["code"] != 200:
                return f"获取详情失败: {data.get('msg', '未知错误')}"
            
            # 构建详细信息和音乐链接，并用<details>标签包裹
            if __event_emitter__:
                # 开始<details>标签
                await __event_emitter__(
                    {
                        "type": "message",
                        "data": {"content": f"\n<details>\n<summary>歌曲详情 - {data.get('name', '未知')}</summary>\n\n"},
                    }
                )
                
                # 歌曲基本信息
                song_info = f"### 歌曲详情\n\n"
                song_info += f"**歌曲名**: {data.get('name', '未知')}\n"
                song_info += f"**歌手**: {data.get('author', '未知')}\n"
                song_info += f"**歌曲ID**: {data.get('id', '未知')}\n"
                
                # 添加封面图片
                if data.get('img'):
                    song_info += f"**歌曲封面**：[点击查看]({data['img']})\n"
                
                # 添加音乐链接
                if data.get('mp3'):
                    song_info += f"\n### 歌曲链接\n\n"
                    song_info += f"**歌曲链接**：[点击播放]({data['mp3']})\n"
                    song_info += f"**时长**：{data.get('market', '未知')}\n"
                
                # 发送歌曲信息
                await __event_emitter__(
                    {
                        "type": "message",
                        "data": {"content": song_info},
                    }
                )
                
                # 结束<details>标签
                await __event_emitter__(
                    {
                        "type": "message",
                        "data": {"content": "\n</details>\n"},
                    }
                )
            
            # 初始化结果字符串（用于返回）
            result = f"### 歌曲详情\n\n"
            result += f"**歌曲名**: {data.get('name', '未知')}\n"
            result += f"**歌手**: {data.get('author', '未知')}\n"
            result += f"**歌曲ID**: {data.get('id', '未知')}\n"
            result += f"**时长**: {data.get('market', '未知')}\n"
            
            # 添加评论（不包含在details中）
            if data.get('review'):
                review = data['review']
                result += f"\n### 热门评论\n\n"
                result += f"**用户**: {review.get('nickname', '未知')}\n"
                result += f"**时间**: {review.get('timeStr', '未知')}\n"
                result += f"**内容**: {review.get('content', '未知')}\n"
            
            # 添加歌词（不包含在details中）
            if self.user_valves.show_lyrics and data.get('lyric'):
                result += f"\n### 歌词\n\n"
                for line in data['lyric']:
                    result += f"{line.get('time', '')} {line.get('name', '')}\n"
            
            # 添加音乐链接（已在details中添加，这里为了保持返回结果的完整性也添加）
            if data.get('mp3'):
                result += f"\n### 歌曲链接\n\n"
                result += f"**歌曲链接**：[点击播放]({data['mp3']})\n"
                result += f"**时长**：{data.get('market', '未知')}\n"
            
            # 添加引用
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "citation",
                        "data": {
                            "document": [f"歌曲: {data.get('name', '未知')} - {data.get('author', '未知')}"],
                            "metadata": [
                                {
                                    "date_accessed": datetime.now().isoformat(),
                                    "source": "音乐搜索API",
                                }
                            ],
                            "source": {"name": "音乐搜索API", "url": f"https://api.lolimi.cn/API/wydg/?msg={query}&n={song_number}"},
                        },
                    }
                )
            
            # 发送完成状态
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "获取歌曲完成", "done": True},
                    }
                )
            
            return result
        
        except Exception as e:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": f"发生错误: {str(e)}", "done": True},
                    }
                )
            return f"获取详情过程中发生错误: {str(e)}"
"""
title: 音乐搜索工具
author: Roo
author_url: https://github.com/roo
description: 这个工具可以通过API搜索音乐，并获取歌曲详细信息
required_open_webui_version: 0.4.0
requirements: requests
version: 1.0.0
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
    
    async def search_music(self, query: str, __event_emitter__=None) -> str:
        """
        搜索歌曲，并返回搜索结果
        :param query: 要搜索的歌曲名称
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
            result = "### 搜索结果\n\n"
            
            if not data.get("data"):
                return "未找到相关歌曲"
            
            # 构建表格显示搜索结果
            result += "| 序号 | 歌曲名 | 歌手 | 歌曲ID |\n"
            result += "| --- | ------ | ---- | ------ |\n"
            
            for i, song in enumerate(data["data"]):
                result += f"| {i+1} | {song['name']} | {song['singer']} | {song['id']} |\n"
            
            # 发送完成状态
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "搜索完成", "done": True},
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
            return f"搜索过程中发生错误: {str(e)}"
    
    async def get_music_detail(self, query: str, song_number: int, __event_emitter__=None) -> str:
        """
        获取单首歌曲的详细信息
        :param query: 要搜索的歌曲名称
        :param song_number: 歌曲序号（从1开始）
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
            
            # 构建详细信息
            result = f"### 歌曲详情\n\n"
            result += f"**歌曲名**: {data.get('name', '未知')}\n"
            result += f"**歌手**: {data.get('author', '未知')}\n"
            result += f"**歌曲ID**: {data.get('id', '未知')}\n"
            result += f"**时长**: {data.get('market', '未知')}\n"
            
            # 添加封面图片（小尺寸）
            if data.get('img'):
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "message",
                            "data": {"content": f"**歌曲封面**：[点击查看]({data['img']})\n"},
                        }
                    )
            
            # 添加评论
            if data.get('review'):
                review = data['review']
                result += f"\n### 热门评论\n\n"
                result += f"**用户**: {review.get('nickname', '未知')}\n"
                result += f"**时间**: {review.get('timeStr', '未知')}\n"
                result += f"**内容**: {review.get('content', '未知')}\n"
            
            # 添加歌词
            if self.user_valves.show_lyrics and data.get('lyric'):
                result += f"\n### 歌词\n\n"
                for line in data['lyric']:
                    result += f"{line.get('time', '')} {line.get('name', '')}\n"
            
            # 添加音乐链接
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
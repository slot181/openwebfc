"""
title: Gemini Pipe
author_url:https://linux.do/u/coker/summary
author:coker
version: 0.0.6
license: MIT
"""

import json
import random
import httpx
import requests
from typing import List, AsyncGenerator, Callable, Awaitable
from pydantic import BaseModel, Field


class Pipe:
    class Valves(BaseModel):
        GOOGLE_API_KEYS_STR: str = Field(
            default="", description="API Keys for Google, use , to split"
        )
        OPEN_SAFETY: bool = Field(default=False, description="Gemini safety settings")
        BASE_URL: str = Field(
            default="https://generativelanguage.googleapis.com/v1beta",
            description="API Base Url",
        )
        OPEN_SEARCH_INFO: bool = Field(
            default=True, description="Open search info show "
        )
        FILTER_THINKING_TAGS: bool = Field(
            default=True, description="Filter <thinking> tags in thinking content"
        )

    def __init__(self):
        self.type = "manifold"
        self.name = "Google: "
        self.valves = self.Valves()
        self.OPEN_SEARCH_MODELS = ["gemini-2.0-flash-exp"]
        self.OPEN_THINK_MODELS = []

        self.base_url = ""
        self.emitter = None
        self.open_search = False
        self.open_think = False
        self.think_first = True

    def get_google_models(self) -> List[dict]:
        self.base_url = self.valves.BASE_URL
        self.GOOGLE_API_KEYS_LIST = self.valves.GOOGLE_API_KEYS_STR.split(",")
        self.GOOGLE_API_KEY = random.choice(self.GOOGLE_API_KEYS_LIST)
        if not self.GOOGLE_API_KEY:
            return [{"id": "error", "name": f"Error: API Key not found"}]

        try:
            url = f"{self.base_url}/models?key={self.GOOGLE_API_KEY}"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

            data = response.json()
            models = [
                {
                    "id": model["name"].split("/")[-1],
                    "name": model["name"].split("/")[-1],
                }
                for model in data.get("models", [])
                if "generateContent" in model.get("supportedGenerationMethods", [])
            ]
            if self.OPEN_SEARCH_MODELS:
                models.extend(
                    [
                        {
                            "id": model + "-search",
                            "name": model + "-search",
                        }
                        for model in self.OPEN_SEARCH_MODELS
                    ]
                )
            return models
        except Exception as e:
            return [{"id": "error", "name": f"Could not fetch models: {str(e)}"}]

    async def emit_status(
        self,
        message: str = "",
        done: bool = False,
    ):
        if self.emitter:
            await self.emitter(
                {
                    "type": "status",
                    "data": {
                        "description": message,
                        "done": done,
                    },
                }
            )

    def pipes(self) -> List[dict]:
        return self.get_google_models()

    def create_search_link(self, idx, web):
        return f'\n{idx:02d}: [**{web["title"]}**]({web["uri"]})'

    def create_think_info(self, think_info):
        """Process thinking content, filter or format <thinking></thinking> tags"""
        if not think_info or not isinstance(think_info, str):
            return think_info

        # Remove <thinking> and </thinking> tags
        think_info = think_info.replace("<thinking>", "")
        think_info = think_info.replace("</thinking>", "")

        return think_info

    async def do_parts(self, parts):
        if not parts or not isinstance(parts, list):
            return "Error: No parts found"
        if len(parts) == 1:
            if self.open_think and self.think_first:
                self.think_first = False
                # Process thinking content
                processed_thinking = self.create_think_info(parts[0]["text"])
                return (
                    f"\n<details>\n<summary>思考过程</summary>\n"
                    "```thinking…… \n" + processed_thinking
                )
            return parts[0]["text"]
        if len(parts) == 2:
            await self.emit_status(message="😄 思考已结束", done=False)
            self.open_think = False
            if self.think_first:
                self.think_first = False
                # Process thinking content
                processed_thinking = self.create_think_info(parts[0]["text"])
                return (
                    f"\n<details>\n<summary>思考过程</summary>\n"
                    "```thinking…… \n"
                    + processed_thinking
                    + "\n```\n"
                    + "\n</details>\n"
                    + parts[1]["text"]
                )
            return parts[0]["text"] + "\n```\n" + "\n</details>\n" + parts[1]["text"]
        res = ""
        for part in parts:
            res += part["text"]
        return res

    async def pipe(
        self,
        body: dict,
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
    ) -> AsyncGenerator[str, None]:
        self.emitter = __event_emitter__
        self.GOOGLE_API_KEYS_LIST = self.valves.GOOGLE_API_KEYS_STR.split(",")
        self.GOOGLE_API_KEY = random.choice(self.GOOGLE_API_KEYS_LIST)
        self.base_url = self.valves.BASE_URL
        if not self.GOOGLE_API_KEY:
            yield "Error: GOOGLE_API_KEY is not set"
            return
        try:
            model_id = body["model"]
            if "." in model_id:
                model_id = model_id.split(".", 1)[1]
            messages = body["messages"]
            stream = body.get("stream", False)
            # Prepare the request payload
            contents = []
            request_data = {
                "generationConfig": {
                    "temperature": body.get("temperature", 0.7),
                    "topP": body.get("top_p", 0.9),
                    "topK": body.get("top_k", 40),
                    "maxOutputTokens": body.get("max_tokens", 8192),
                    "stopSequences": body.get("stop", []),
                },
            }

            for message in messages:
                if message["role"] == "system":
                    request_data["system_instruction"] = {
                        "parts": [{"text": message["content"]}]
                    }
                if message["role"] != "system":
                    if isinstance(message.get("content"), str):
                        contents.append(
                            {
                                "role": (
                                    "user" if message["role"] == "user" else "model"
                                ),
                                "parts": [{"text": message["content"]}],
                            }
                        )
                    if isinstance(message.get("content"), list):
                        parts = []
                        for content in message["content"]:
                            if content["type"] == "text":
                                parts.append({"text": content["text"]})
                            elif content["type"] == "image_url":
                                image_url = content["image_url"]["url"]
                                if image_url.startswith("data:image"):
                                    image_data = image_url.split(",")[1]
                                    parts.append(
                                        {
                                            "inline_data": {
                                                "mime_type": "image/jpeg",
                                                "data": image_data,
                                            }
                                        }
                                    )
                                else:
                                    parts.append({"image_url": image_url})
                        contents.append(
                            {
                                "role": (
                                    "user" if message["role"] == "user" else "model"
                                ),
                                "parts": parts,
                            }
                        )
            request_data["contents"] = contents
            if model_id.endswith("-search"):
                model_id = model_id[:-7]
                request_data["tools"] = [{"googleSearch": {}}]
                self.open_search = True
                await self.emit_status(message="🔍 我好像在搜索……")
            elif model_id in self.OPEN_THINK_MODELS:
                await self.emit_status(message="🧐 我好像在思考……")
                self.open_think = True
                self.think_first = True
            else:
                await self.emit_status(message="🚀 飞速生成中……")
            if self.valves.OPEN_SAFETY:
                request_data["safetySettings"] = [
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
                ]
            params = {"key": self.GOOGLE_API_KEY}
            if stream:
                url = f"{self.base_url}/models/{model_id}:streamGenerateContent"
                params["alt"] = "sse"
            else:
                url = f"{self.base_url}/models/{model_id}:generateContent"
            headers = {"Content-Type": "application/json"}
            async with httpx.AsyncClient() as client:
                if stream:
                    async with client.stream(
                        "POST",
                        url,
                        json=request_data,
                        headers=headers,
                        params=params,
                        timeout=120,
                    ) as response:
                        if response.status_code != 200:
                            yield f"Error: HTTP {response.status_code}: {response.text}"
                            await self.emit_status(message="❌ 生成失败", done=True)
                            return

                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])
                                    if "candidates" in data and data["candidates"]:
                                        parts = data["candidates"][0]["content"][
                                            "parts"
                                        ]
                                        text = await self.do_parts(parts)
                                        yield text
                                        try:
                                            if (
                                                self.open_search
                                                and self.valves.OPEN_SEARCH_INFO
                                                and data["candidates"][0][
                                                    "groundingMetadata"
                                                ]["groundingChunks"]
                                            ):
                                                yield "\n---------------------------------\n"
                                                groundingChunks = data["candidates"][0][
                                                    "groundingMetadata"
                                                ]["groundingChunks"]
                                                for idx, groundingChunk in enumerate(
                                                    groundingChunks, 1
                                                ):
                                                    if "web" in groundingChunk:
                                                        yield self.create_search_link(
                                                            idx, groundingChunk["web"]
                                                        )
                                        except Exception as e:
                                            pass
                                except Exception as e:
                                    yield f"Error parsing stream: {str(e)}"
                        await self.emit_status(message="🎉 生成成功", done=True)
                else:
                    response = await client.post(
                        url,
                        json=request_data,
                        headers=headers,
                        params=params,
                        timeout=120,
                    )
                    if response.status_code != 200:
                        yield f"Error: HTTP {response.status_code}: {response.text}"
                        return
                    data = response.json()
                    res = ""
                    if "candidates" in data and data["candidates"]:
                        parts = data["candidates"][0]["content"]["parts"]
                        res = await self.do_parts(parts)
                        try:
                            if (
                                self.open_search
                                and self.valves.OPEN_SEARCH_INFO
                                and data["candidates"][0]["groundingMetadata"][
                                    "groundingChunks"
                                ]
                            ):
                                res += "\n---------------------------------\n"
                                groundingChunks = data["candidates"][0][
                                    "groundingMetadata"
                                ]["groundingChunks"]
                                for idx, groundingChunk in enumerate(
                                    groundingChunks, 1
                                ):
                                    if "web" in groundingChunk:
                                        res += self.create_search_link(
                                            idx, groundingChunk["web"]
                                        )
                        except Exception as e:
                            pass
                        await self.emit_status(message="🎉 生成成功", done=True)
                        yield res
                        return
                    else:
                        yield "No response data"
                    return
        except Exception as e:
            yield f"Error: {str(e)}"
            await self.emit_status(message="❌ 生成失败", done=True)

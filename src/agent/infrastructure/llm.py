"""DeepSeek 大模型客户端封装（兼容 OpenAI 协议）。"""
import os
from typing import Any

from openai import OpenAI


class DeepSeekLLM:
    """封装 DeepSeek 的 OpenAI 兼容接口，负责单次/多轮工具调用。"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        # 未配置 key 时延迟到 chat() 再报错，避免应用启动即失败
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None

    def _require_client(self) -> None:
        if not self.api_key or self.client is None:
            raise RuntimeError(
                "未配置 DEEPSEEK_API_KEY，无法调用大模型。"
                "请在项目根目录 .env 文件中填写（参考 .env.example）。"
            )

    def configure(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> None:
        """运行时更新 LLM 配置（用户在前端设置页输入后动态生效）。"""
        if api_key:
            self.api_key = api_key
        if base_url:
            self.base_url = base_url
        if model:
            self.model = model
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None

    def chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        """单次对话，返回模型文本输出。"""
        self._require_client()
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            stream=False,
        )
        return resp.choices[0].message.content or ""

    def chat_messages(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
    ) -> Any:
        """多轮对话，支持 function calling；返回完整 message 对象。"""
        self._require_client()
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message

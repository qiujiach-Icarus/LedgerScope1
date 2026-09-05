"""DeepSeek 大模型客户端封装（兼容 OpenAI 协议）。"""
import os

from openai import OpenAI


class DeepSeekLLM:
    """封装 DeepSeek 的 OpenAI 兼容接口，负责单次对话调用。"""

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

    def chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        """单次对话，返回模型文本输出。"""
        if not self.api_key or self.client is None:
            raise RuntimeError(
                "未配置 DEEPSEEK_API_KEY，无法调用大模型。"
                "请在项目根目录 .env 文件中填写（参考 .env.example）。"
            )
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

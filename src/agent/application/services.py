"""风险分析归因 Agent：将 skill 作为 system prompt，对风险载荷做单次归因推理。"""
import json
from pathlib import Path

from ..infrastructure.llm import DeepSeekLLM

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# 按固定顺序拼接，确保 skill 主指令在前、补充说明在后
_PROMPT_ORDER = ["skill.md", "evidence_classification.md", "report_template.md", "example_analysis.md"]


class AttributionAgent:
    """加载 skill 作为 system prompt，把风险载荷序列化后交给 LLM 生成八段式归因报告。"""

    def __init__(self, llm: DeepSeekLLM | None = None):
        self.llm = llm or DeepSeekLLM()
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        parts = []
        for name in _PROMPT_ORDER:
            path = PROMPTS_DIR / name
            if path.exists():
                parts.append(path.read_text(encoding="utf-8"))
        return "\n\n".join(parts)

    def analyze(self, payload: dict) -> str:
        """输入风险载荷，返回八段式归因报告文本（Markdown）。"""
        user = json.dumps(payload, ensure_ascii=False, indent=2)
        return self.llm.chat(system=self.system_prompt, user=user)

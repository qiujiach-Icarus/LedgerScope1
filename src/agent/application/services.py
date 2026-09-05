"""风险分析归因 Agent：planner → 领域专家 → 汇总报告的多 Agent 编排。

每个领域专家都通过确定性工具做真实校验，并记录「工具调用 + 结论」trace，
供前端以 Agent 化视图展示思考、调用与结论。
"""
import json
from pathlib import Path

from ..infrastructure.llm import DeepSeekLLM
from ..infrastructure.tools import execute_tool, tool_schemas_for
from .specialists import (
    SPECIALIST_PROMPTS,
    SPECIALIST_TOOLS,
    PLANNER_SYSTEM,
    PLAN_TOOL_SCHEMA,
)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# 按固定顺序拼接，确保 skill 主指令在前、补充说明在后
_PROMPT_ORDER = ["skill.md", "evidence_classification.md", "report_template.md", "example_analysis.md"]

# 每个专家最多允许的工具调用轮次，防止无限调用
MAX_TOOL_ROUNDS = 4

TOOL_USAGE = """

## 工具使用规则（必须遵守）
你必须通过工具获取并验证数据，禁止凭空编造金额、日期、供应商或验证结果。
工具返回的 JSON 是唯一事实来源；数据未接入或工具未返回的，一律标为「未提供/无法验证」，
不得声称系统已验证。完成后用纯文本输出你的核对结论。
"""

REPORT_USAGE = """

## 汇总要求（必须遵守）
下面是各领域专家的调查结论。请把它们综合成一份八段式归因报告（① 风险概览 ② 为什么异常
③ 风险归因 ④ 可能影响什么 ⑤ 已有数据验证 ⑥ 证据缺口 ⑦ 建议查什么 ⑧ AI 审计建议）。
只能引用专家结论中出现的确定性结果，禁止编造金额、日期、供应商或验证结果。
"""


class AttributionAgent:
    """planner → 领域专家 → 汇总报告的多 Agent 归因编排器。"""

    def __init__(self, llm: DeepSeekLLM | None = None):
        self.llm = llm or DeepSeekLLM()
        self.base_system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        parts = []
        for name in _PROMPT_ORDER:
            path = PROMPTS_DIR / name
            if path.exists():
                parts.append(path.read_text(encoding="utf-8"))
        return "\n\n".join(parts)

    @staticmethod
    def _build_context(payload: dict) -> dict:
        """只把风险概览与数据表清单发给模型，大块证据行由工具按需返回，避免上下文爆掉。"""
        context = dict(payload)
        ad = context.get("available_data")
        if isinstance(ad, dict):
            context["available_data"] = {
                "tables_loaded": ad.get("tables_loaded", []),
                "entity": ad.get("entity", {}),
            }
        return context

    def _plan(self, context: dict) -> list[str]:
        """调用 planner 决定需要派发哪些领域专家。"""
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False, indent=2)},
        ]
        msg = self.llm.chat_messages(messages, tools=PLAN_TOOL_SCHEMA)
        tool_calls = getattr(msg, "tool_calls", None)

        names: list[str] = []
        if tool_calls:
            try:
                args = json.loads(tool_calls[0].function.arguments or "{}")
                names = list(args.get("specialists", []))
            except (TypeError, ValueError):
                names = []

        names = [n for n in names if n in SPECIALIST_TOOLS]
        return names or list(SPECIALIST_TOOLS.keys())

    def _run_specialist(self, name: str, context: dict, payload: dict) -> dict:
        """运行单个领域专家，返回工具调用 trace 与最终结论。"""
        tools = tool_schemas_for(SPECIALIST_TOOLS[name])
        messages = [
            {"role": "system", "content": SPECIALIST_PROMPTS[name] + TOOL_USAGE},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False, indent=2)},
        ]

        tool_calls_trace: list[dict] = []
        conclusion = ""
        for _ in range(MAX_TOOL_ROUNDS):
            msg = self.llm.chat_messages(messages, tools=tools)
            messages.append(msg)

            calls = getattr(msg, "tool_calls", None)
            if not calls:
                conclusion = msg.content or ""
                break

            for tc in calls:
                args_json = tc.function.arguments
                result = execute_tool(tc.function.name, args_json, payload)
                tool_calls_trace.append({
                    "tool": tc.function.name,
                    "args": args_json,
                    "result": result,
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        return {
            "specialist": name,
            "tool_calls": tool_calls_trace,
            "conclusion": conclusion or "（该专家未产出结论）",
        }

    def _report(self, context: dict, steps: list[dict]) -> str:
        """汇总各专家结论，生成最终八段式报告。"""
        system = self.base_system_prompt + REPORT_USAGE
        user = json.dumps(
            {"risk_context": context, "specialist_findings": steps},
            ensure_ascii=False,
            indent=2,
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        msg = self.llm.chat_messages(messages)
        return msg.content or ""

    def analyze_with_trace(self, payload: dict) -> dict:
        """返回报告文本 + 专家编排与工具调用 trace，供前端 Agent 化展示。"""
        context = self._build_context(payload)
        specialists = self._plan(context)
        steps = [self._run_specialist(name, context, payload) for name in specialists]
        report = self._report(context, steps)
        return {
            "report": report,
            "specialists": specialists,
            "steps": steps,
        }

    def analyze(self, payload: dict) -> str:
        """兼容旧接口：只返回报告文本。"""
        return self.analyze_with_trace(payload)["report"]

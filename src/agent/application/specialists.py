"""领域专家配置与审计规划器。

借鉴 FinCA 的横向领域切分：把单一归因 Agent 拆成凭证 / 发票 / 银行 / 报表 / 供应商
五个领域专家，每个专家只负责自己的维度、只能调用自己的工具白名单。
"""
from typing import Any

# 每个专家的专属工具白名单（最小权限）
SPECIALIST_TOOLS: dict[str, list[str]] = {
    "voucher": ["list_available_data", "get_voucher_details", "three_way_compare"],
    "invoice": ["list_available_data", "detect_duplicate_invoice", "three_way_compare"],
    "bank": ["list_available_data", "three_way_compare"],
    "statement": ["list_available_data", "get_financial_statements"],
    "vendor": ["list_available_data", "vendor_trend"],
}

# 每个专家的专属 system prompt（只调查本领域，不写最终报告）
SPECIALIST_PROMPTS: dict[str, str] = {
    "voucher": (
        "你是财务审计中的「凭证专家」。只负责核对会计凭证：借贷方向、金额、科目、日期、摘要。\n"
        "不要扩展到发票、银行流水或供应商。基于工具返回的确定性结果给出核对结论。\n"
        "输出格式（纯文本，不要 Markdown 大标题）：凭证核对结论（含金额/科目/方向/异常点）。"
    ),
    "invoice": (
        "你是财务审计中的「发票专家」。只负责发票相关：发票号码查重、价税金额核对、发票与凭证勾稽。\n"
        "不要扩展到银行流水或供应商趋势。基于工具返回的确定性结果给出核对结论。\n"
        "输出格式（纯文本）：发票核对结论（含重复发票/金额差异）。"
    ),
    "bank": (
        "你是财务审计中的「银行流水专家」。只负责付款/收款流水与凭证金额的比对、资金流向核对。\n"
        "不要扩展到发票或供应商。基于工具返回的确定性结果给出核对结论。\n"
        "输出格式（纯文本）：银行流水核对结论（含付款金额/差异）。"
    ),
    "statement": (
        "你是财务审计中的「报表专家」。只负责财务报表的勾稽关系与结构异常分析。\n"
        "不要扩展到明细凭证或供应商。基于工具返回的财务报表数据给出核对结论。\n"
        "输出格式（纯文本）：报表勾稽结论（含差异金额/异常科目）。"
    ),
    "vendor": (
        "你是财务审计中的「供应商/客户专家」。只负责供应商/客户交易趋势、集中度、关联异常。\n"
        "不要扩展到发票细节或报表勾稽。基于工具返回的确定性结果给出核对结论。\n"
        "输出格式（纯文本）：供应商/客户趋势结论（含金额合计/趋势异常）。"
    ),
}

# 审计规划器 system prompt
PLANNER_SYSTEM = (
    "你是审计调查规划器。根据风险概览（risk_score / risk_level / object / anomaly_factors / "
    "可用数据表），决定需要派发哪些领域专家参与本次调查。\n"
    "可选专家：voucher（凭证）、invoice（发票）、bank（银行流水）、statement（报表）、vendor（供应商/客户）。\n"
    "只选择与该风险真正相关的专家，避免全量派发。调用 plan_investigation 工具返回 specialists 列表。"
)

# 规划器 function calling schema（用于解析派发结果）
PLAN_TOOL_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "plan_investigation",
            "description": "决定本次审计需要派发哪些领域专家。",
            "parameters": {
                "type": "object",
                "properties": {
                    "specialists": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["voucher", "invoice", "bank", "statement", "vendor"],
                        },
                        "description": "需要派发的领域专家列表",
                    }
                },
                "required": ["specialists"],
            },
        },
    },
]

VALID_SPECIALISTS = set(SPECIALIST_TOOLS.keys())

"""审计 Agent 的双护栏：输入防注入 + 输出防越界。

审计数据来自外部 Excel，凭证摘要 / 供应商名等字段可能夹带提示词注入；
输出端需拦截「把建议调取资料说成已验证」或「直接认定舞弊」等越界表述。
"""
import re
from typing import Any

# 提示词注入特征（中英混排，宁可多报不可漏报）
_INJECTION_PATTERNS = [
    r"忽略.{0,6}(以上|之前|系统).{0,6}(指令|提示|规则|设定)",
    r"ignore\s+(all\s+)?(previous|above|system)\s+(instructions?|prompts?|rules?)",
    r"你现在.{0,4}(是|扮演|作为)",
    r"(现在|请).{0,4}以.{0,10}(身份|角色).{0,6}(回答|输出)",
    r"system\s*prompt",
    r"你是一个\s*[A-Za-z]",
    r"忽略角色设定",
    r"越狱|jailbreak",
]

# 输出端过度定性词（不得仅凭异常数据直接认定舞弊/造假）
_OVERCLAIM_PATTERNS = [
    r"确认(存在)?舞弊",
    r"认定(为|存在)?(舞弊|造假|欺诈)",
    r"已(查明|证实|确认)(财务)?造假",
    r"构成(财务)?欺诈",
    r"合同显示",
    r"发票证明",
    r"银行流水显示(该)?交易(真实|虚假)",
    r"会议纪要表明",
    r"邮件表明",
]


def _field_text(payload: dict) -> str:
    """抽取需要做输入护栏的字符串字段。"""
    obj = payload.get("object") or {}
    parts = [
        str(obj.get("voucher_id", "")),
        str(obj.get("account", "")),
        str(obj.get("summary", "")),
        str(obj.get("date", "")),
    ]
    ad = payload.get("available_data") or {}
    entity = ad.get("entity") or {}
    parts.extend(str(v) for v in entity.values())
    return "\n".join(parts)


def detect_prompt_injection(payload: dict) -> str | None:
    """检测输入载荷中的提示词注入，返回违规描述或 None。"""
    text = _field_text(payload)
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return f"检测到疑似提示词注入：{pattern}"
    return None


def validate_output(report: str) -> list[str]:
    """输出护栏：返回过度定性 / 越界表述的违规项列表。"""
    violations = []
    for pattern in _OVERCLAIM_PATTERNS:
        if re.search(pattern, report, flags=re.IGNORECASE):
            violations.append(pattern)
    return violations

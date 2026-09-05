"""确定性审计工具层。

把「让 LLM 心算」升级为「代码确定性计算」：每个工具都基于 payload 中已接入的
结构化数据（available_data）做真实校验，返回 JSON 可序列化的确定性结果，
供 LLM 通过 function calling 调用后解读，从而形成可追溯的证据链。
"""
import json
from collections import Counter
from typing import Any, Callable

# 金额列候选（按优先级尝试）
AMOUNT_COLUMNS = [
    "价税合计", "金额", "交易金额", "发生额", "付款金额", "收款金额",
    "借方金额", "贷方金额", "本币金额",
]

# 发票号列候选
INVOICE_NO_COLUMNS = [
    "发票号码", "发票号", "发票编号", "发票代码", "invoice_no",
]

# 供应商/客户实体列候选
ENTITY_COLUMNS = [
    "供应商编号", "供应商名称", "客户编号", "客户名称", "对方编号", "对方名称",
]


def _to_float(value: Any) -> float | None:
    """安全转 float，None/NaN/非法值返回 None。"""
    if value is None:
        return None
    try:
        f = float(value)
        return None if f != f else f
    except (TypeError, ValueError):
        return None


def _pick_column(rows: list[dict], candidates: list[str]) -> list[Any]:
    """返回第一个存在的候选列的原始值列表。"""
    for col in candidates:
        if any(r.get(col) is not None for r in rows):
            return [r.get(col) for r in rows]
    return []


def _amounts(rows: list[dict]) -> list[float]:
    """提取行列表中的金额序列（过滤 None）。"""
    for col in AMOUNT_COLUMNS:
        vals = [a for r in rows if (a := _to_float(r.get(col))) is not None]
        if vals:
            return vals
    return []


def _closest(values: list[float], target: float | None) -> float | None:
    if not values or target is None:
        return None
    return min(values, key=lambda x: abs(x - target))


def _diff(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return round(a - b, 2)


def _evidence(payload: dict) -> dict[str, Any]:
    return ((payload.get("available_data") or {}).get("evidence")) or {}


# --------------------------- 工具实现 ---------------------------

def tool_list_available_data(payload: dict, args: dict) -> dict:
    """列出当前项目已接入、可直接验证的数据范围。"""
    ad = payload.get("available_data") or {}
    evidence = ad.get("evidence") or {}
    return {
        "tables_loaded": ad.get("tables_loaded", []),
        "entity": ad.get("entity", {}),
        "evidence_tables": {
            sheet: {
                "matched_by": info.get("matched_by", ""),
                "row_count": len(info.get("rows") or []),
            }
            for sheet, info in evidence.items()
        },
        "statement_tables": {
            sheet: len(rows) for sheet, rows in (ad.get("financial_statements") or {}).items()
        },
        "meta_tables": {
            sheet: len(rows) for sheet, rows in (ad.get("meta") or {}).items()
        },
    }


def tool_three_way_compare(payload: dict, args: dict) -> dict:
    """凭证金额 vs 发票金额 vs 银行付款金额 的三方比对。"""
    obj = payload.get("object") or {}
    voucher_amount = _to_float(obj.get("amount"))
    evidence = _evidence(payload)
    invoice_rows = (evidence.get("发票明细") or {}).get("rows") or []
    bank_rows = (evidence.get("银行流水") or {}).get("rows") or []

    invoice_amounts = _amounts(invoice_rows)
    bank_amounts = _amounts(bank_rows)
    closest_invoice = _closest(invoice_amounts, voucher_amount)
    closest_bank = _closest(bank_amounts, voucher_amount)

    return {
        "voucher_amount": voucher_amount,
        "invoice_amounts": invoice_amounts,
        "bank_amounts": bank_amounts,
        "closest_invoice": closest_invoice,
        "closest_bank": closest_bank,
        "invoice_vs_voucher_diff": _diff(closest_invoice, voucher_amount),
        "bank_vs_voucher_diff": _diff(closest_bank, voucher_amount),
    }


def _safe_text(value: Any) -> str | None:
    """安全转非空字符串，None/NaN/占位符返回 None。"""
    if value is None:
        return None
    try:
        if value != value:  # NaN
            return None
    except Exception:
        pass
    s = str(value).strip()
    if s.lower() in ("", "nan", "none", "nat"):
        return None
    return s


def tool_detect_duplicate_invoice(payload: dict, args: dict) -> dict:
    """在已接入的发票明细里按发票号查重。"""
    evidence = _evidence(payload)
    invoice_rows = (evidence.get("发票明细") or {}).get("rows") or []
    nos = [s for v in _pick_column(invoice_rows, INVOICE_NO_COLUMNS)
           if (s := _safe_text(v)) is not None]
    duplicates = {no: cnt for no, cnt in Counter(nos).items() if cnt > 1}
    return {
        "invoice_row_count": len(invoice_rows),
        "invoice_number_count": len(nos),
        "duplicates": duplicates,
    }


def tool_vendor_trend(payload: dict, args: dict) -> dict:
    """按供应商/客户聚合其在采购/应收/应付/销售等表中的金额与行数。"""
    ad = payload.get("available_data") or {}
    entity = ad.get("entity") or {}
    vendor = args.get("vendor_id") or next(
        (entity.get(c) for c in ENTITY_COLUMNS if entity.get(c)), None
    )
    evidence = ad.get("evidence") or {}

    def _aggregate(rows: list[dict]) -> dict:
        if vendor:
            rows = [
                r for r in rows
                if any(str(r.get(c)).strip() == str(vendor)
                       for c in ENTITY_COLUMNS if r.get(c) is not None)
            ]
        amounts = _amounts(rows)
        return {
            "row_count": len(rows),
            "amount_total": round(sum(amounts), 2) if amounts else 0,
            "amounts": amounts[:20],
        }

    by_table = {
        sheet: _aggregate((info.get("rows") or []))
        for sheet, info in evidence.items()
        if sheet in {"采购明细", "应付账款台账", "应收账款台账", "销售明细"}
    }
    return {"vendor": vendor, "by_table": by_table}


def tool_get_voucher_details(payload: dict, args: dict) -> dict:
    """返回当前凭证的核心字段，供凭证专家核对。"""
    obj = payload.get("object") or {}
    return {
        "voucher_id": obj.get("voucher_id"),
        "account": obj.get("account"),
        "amount": obj.get("amount"),
        "date": obj.get("date"),
        "summary": obj.get("summary"),
        "deviation_ratio": obj.get("deviation_ratio"),
    }


def tool_get_financial_statements(payload: dict, args: dict) -> dict:
    """返回已接入的财务报表与元数据，供报表专家做勾稽与结构分析。"""
    ad = payload.get("available_data") or {}
    return {
        "financial_statements": ad.get("financial_statements") or {},
        "meta": ad.get("meta") or {},
    }


TOOL_IMPLEMENTATIONS: dict[str, Callable[[dict, dict], dict]] = {
    "list_available_data": tool_list_available_data,
    "three_way_compare": tool_three_way_compare,
    "detect_duplicate_invoice": tool_detect_duplicate_invoice,
    "vendor_trend": tool_vendor_trend,
    "get_voucher_details": tool_get_voucher_details,
    "get_financial_statements": tool_get_financial_statements,
}


# --------------------------- OpenAI function schemas ---------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_available_data",
            "description": "列出当前项目已接入、可直接验证的数据表及其行数，用于判断 A 类证据范围。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "three_way_compare",
            "description": "比对当前凭证金额、发票金额、银行付款金额三方是否一致，返回确定性差异。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_duplicate_invoice",
            "description": "在发票明细中按发票号码查重，返回重复发票号及出现次数。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vendor_trend",
            "description": "按供应商/客户聚合采购、应付、应收、销售等表中的金额与行数，用于趋势判断。",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor_id": {
                        "type": "string",
                        "description": "供应商或客户编号/名称；缺省时自动使用当前凭证的实体标识。",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_voucher_details",
            "description": "返回当前凭证的核心字段（科目、金额、日期、摘要、偏离倍数），供凭证核对。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_statements",
            "description": "返回已接入的财务报表与元数据，供报表勾稽与结构分析。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def tool_schemas_for(names: list[str]) -> list[dict[str, Any]]:
    """按工具名白名单过滤 schema，实现最小权限工具注册表。"""
    return [s for s in TOOL_SCHEMAS if s["function"]["name"] in names]


def execute_tool(name: str, arguments_json: str, payload: dict) -> dict:
    """执行指定工具，返回 JSON 可序列化的确定性结果。"""
    impl = TOOL_IMPLEMENTATIONS.get(name)
    if impl is None:
        return {"error": f"未知工具 {name}"}

    try:
        args = json.loads(arguments_json) if arguments_json else {}
    except (TypeError, ValueError):
        args = {}

    if not isinstance(args, dict):
        args = {}

    try:
        return impl(payload, args)
    except Exception as e:  # 工具失败不应让整个请求崩溃
        return {"error": f"工具 {name} 执行失败：{e}"}

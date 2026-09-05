"""把检测结果的一行数据映射为 skill 需要的输入 JSON。

核心：`build_available_data` 把已读入的多表数据（华辰 11 类）按目标凭证的实体
（供应商编号/名称、客户编号等）检索出相关行，装进 `available_data`，让 LLM 真正
拿到可交叉验证的数据，而不是只有文件名。
"""
from typing import Any

import pandas as pd

from config.table_types import (
    SHEET_TYPE_MAP,
    EVIDENCE_TYPES,
    STATEMENT_TYPES,
    META_TYPES,
    ENTITY_ID_COLUMNS,
    MAX_EVIDENCE_ROWS,
)


def _map_risk_level(score: float) -> str:
    if score >= 70:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def _parse_factors(diagnosis: Any) -> list[dict]:
    """把「异常原因诊断」文本解析为 anomaly_factors 结构。"""
    if not diagnosis:
        return [{"dimension": "combination", "description": "多维特征组合离群", "severity": "medium"}]

    keyword_map = [
        ("金额", "amount", "high"),
        ("非工作日", "time", "medium"),
        ("年末", "time", "medium"),
        ("年初", "time", "medium"),
        ("组合", "combination", "medium"),
    ]
    factors: list[dict] = []
    seen: set[str] = set()
    for raw in str(diagnosis).split("、"):
        text = raw.strip()
        if not text:
            continue
        for kw, dim, sev in keyword_map:
            if kw in text:
                if dim not in seen:
                    factors.append({"dimension": dim, "description": text, "severity": sev})
                    seen.add(dim)
                break
        else:
            if "other" not in seen:
                factors.append({"dimension": "other", "description": text, "severity": "medium"})
                seen.add("other")
    return factors


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


def _as_text(value: Any) -> str:
    """把值安全转成字符串，None / NaN 返回空串。"""
    if value is None:
        return ""
    try:
        if value != value:  # NaN
            return ""
    except Exception:
        pass
    return str(value)


def _clean_value(value: Any) -> Any:
    """把 DataFrame 单元格转成 JSON 可序列化的值；None/NaN 返回 None。"""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, (int, str, bool)):
        return value
    return str(value)


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> 行 dict 列表，清洗 NaN/时间戳，保证可 JSON 序列化。"""
    records = []
    for _, r in df.iterrows():
        rec = {}
        for col, val in r.items():
            cleaned = _clean_value(val)
            if cleaned is not None:
                rec[str(col)] = cleaned
        records.append(rec)
    return records


def normalize_voucher_id(value: Any) -> str:
    """把 float 形式的凭证号（如 1.0）规范化为 '1'。"""
    s = _as_text(value).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _extract_entity(voucher_row: dict) -> dict[str, str]:
    """从凭证行提取实体标识（供应商编号/名称、客户编号/名称等）。"""
    entity: dict[str, str] = {}
    for col in ENTITY_ID_COLUMNS:
        val = voucher_row.get(col)
        if val is None:
            continue
        text = _as_text(val).strip()
        if text and text.lower() not in ("nan", "none", "nat"):
            entity[col] = text
    return entity


def _retrieve_related(df: pd.DataFrame, entity: dict[str, str]) -> tuple[list[dict] | None, str]:
    """在证据表里按实体值检索相关行。返回 (rows, matched_by)。"""
    if not entity:
        return None, ""
    id_cols = [c for c in ENTITY_ID_COLUMNS if c in df.columns]
    if not id_cols:
        return None, ""

    mask = pd.Series(False, index=df.index)
    matched_keys: list[str] = []
    for col in id_cols:
        col_values = df[col].astype(str).str.strip()
        for key, val in entity.items():
            col_mask = col_values == val
            if col_mask.any():
                mask = mask | col_mask
                matched_keys.append(f"{col}={val}")

    if not mask.any():
        return None, ""

    sub = df[mask]
    truncated = len(sub) > MAX_EVIDENCE_ROWS
    if truncated:
        sub = sub.head(MAX_EVIDENCE_ROWS)

    rows = _df_to_records(sub)
    if truncated:
        rows.append({"_truncated": f"匹配行过多，已截断至前 {MAX_EVIDENCE_ROWS} 行"})

    matched_by = "、".join(dict.fromkeys(matched_keys))
    return rows, matched_by


def build_available_data(tables: dict[str, pd.DataFrame] | None, voucher_row: dict) -> dict[str, Any]:
    """构造富化的 available_data：表清单 + 按实体检索的证据行 + 报表/元数据全量。"""
    if not tables:
        return {"tables_loaded": [], "evidence": {}, "entity": {}}

    entity = _extract_entity(voucher_row)

    evidence: dict[str, Any] = {}
    statements: dict[str, Any] = {}
    meta: dict[str, Any] = {}

    for sheet, df in tables.items():
        table_type = SHEET_TYPE_MAP.get(sheet)
        if table_type in EVIDENCE_TYPES:
            rows, matched_by = _retrieve_related(df, entity)
            if rows is not None:
                evidence[sheet] = {"matched_by": matched_by, "rows": rows}
        elif table_type in STATEMENT_TYPES:
            statements[sheet] = _df_to_records(df)
        elif table_type in META_TYPES:
            meta[sheet] = _df_to_records(df)

    result: dict[str, Any] = {
        "tables_loaded": list(tables.keys()),
        "entity": entity,
        "evidence": evidence,
    }
    if statements:
        result["financial_statements"] = statements
    if meta:
        result["meta"] = meta
    return result


def build_risk_payload(row: dict[str, Any], tables: dict[str, pd.DataFrame] | None = None) -> dict[str, Any]:
    """把 DataFrame 的一行（dict）映射为 skill 的输入 JSON。"""
    score = _as_float(row.get("风险评分")) or 0.0

    return {
        "risk_score": round(score, 2),
        "risk_level": _map_risk_level(score),
        "risk_type": "异常凭证",
        "object": {
            "voucher_id": normalize_voucher_id(row.get("voucher_id")),
            "account": _as_text(row.get("account")),
            "amount": _as_float(row.get("amount")),
            "date": _as_text(row.get("date"))[:10],
            "summary": _as_text(row.get("摘要")),
            "deviation_ratio": _as_float(row.get("偏离倍数")),
            # 补充结构化数值，供交叉验证引用
            "科目历史均值": _as_float(row.get("科目历史均值")),
            "平滑参考基准": _as_float(row.get("平滑参考基准")),
            "异常原因诊断": _as_text(row.get("异常原因诊断")),
        },
        "anomaly_factors": _parse_factors(row.get("异常原因诊断")),
        "available_data": build_available_data(tables, row),
    }

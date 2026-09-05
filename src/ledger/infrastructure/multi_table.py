"""多表数据加载：把一张 Excel 里的多类表（华辰 11 类）按类型各自读成独立 DataFrame。

与 loaders.py（单凭证表管线）的区别：
- 这里按 sheet 名精确分类（config.table_types.SHEET_TYPE_MAP），不猜表头。
- 会计凭证 sheet 会被「凭证化」（生成 amount/direction/month/day_of_week 等），
  以便复用现有 pattern/anomaly 检测管线；其余表保留原始中文列，作为证据库喂给 LLM。
"""
import pandas as pd

from config.table_types import SHEET_TYPE_MAP
from .loaders import ExcelLoader

# 会计凭证 sheet 的字段 -> 标准字段（其余列如 摘要/供应商编号/供应商名称/部门/风险标签 保留原名）
VOUCHER_RENAME = {
    "凭证号": "voucher_id",
    "日期": "date",
    "科目": "account",
    "借方金额": "debit",
    "贷方金额": "credit",
}


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """去全空行、全空列，重置索引。"""
    df = df.dropna(how="all").dropna(axis=1, how="all")
    return df.reset_index(drop=True)


def _voucherize(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    """把会计凭证原始表转成凭证化 DataFrame（复用 loaders 的维度构建）。"""
    rename = {k: v for k, v in VOUCHER_RENAME.items() if k in df.columns}
    df = df.rename(columns=rename)
    loader = ExcelLoader()
    return loader.build_dimensions(df, rename, excel_header_row=1, sheet_name=sheet_name)


def load_multi_table(excel_path: str) -> dict[str, pd.DataFrame]:
    """读入所有可识别类型表，返回 {sheet_name: DataFrame}。

    sheet 名（中文）作 key，便于 LLM 直接理解；未在 SHEET_TYPE_MAP 中的 sheet
    （如「使用说明」「Ground_Truth」）被跳过。
    """
    tables: dict[str, pd.DataFrame] = {}

    # 用 with 管理 ExcelFile 句柄，退出时自动 close，
    # 避免 upload 的 finally 里 os.remove(temp_path) 因文件被占用而 PermissionError。
    with pd.ExcelFile(excel_path) as xl:
        for sheet in xl.sheet_names:
            table_type = SHEET_TYPE_MAP.get(sheet)
            if table_type is None:
                continue

            df_raw = xl.parse(sheet_name=sheet, header=0)
            if table_type == "voucher":
                df = _voucherize(df_raw, sheet)
            else:
                df = _clean(df_raw)

            tables[sheet] = df

    return tables

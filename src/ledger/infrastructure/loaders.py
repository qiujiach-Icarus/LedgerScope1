import numpy as np
import pandas as pd
from fuzzywuzzy import process
from config.column_synonyms import COLUMN_SYNONYMS

class ExcelLoader:
    def __init__(self, fuzzy_threshold: int = 80):
        self.fuzzy_threshold = fuzzy_threshold
        self._build_reverse_map()
        self.summary_keywords = ["总表", "汇总", "总账", "合并"]
        self.detect_groups = [
            ["借方", "贷方", "科目"],
            ["凭证号", "价税合计", "发票号码"]
        ]
        self.skip_sheets = ["工资"]
        self.meta_trace = {}

    def _build_reverse_map(self):
        self.reverse_map = {}
        for std_name, synonyms in COLUMN_SYNONYMS.items():
            for syn in synonyms:
                clean_syn = str(syn).replace(" ", "").lower()
                self.reverse_map[clean_syn] = std_name

    def normalize_columns(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict, list]:
        rename_map = {}
        unmatched = []
        assigned_targets = set()

        for col_raw in df.columns:
            col_clean = str(col_raw).replace(" ", "").lower()
            if not col_clean or "对方" in col_clean or col_clean == "日":
                unmatched.append(col_raw)
                continue

            if col_clean in self.reverse_map:
                target = self.reverse_map[col_clean]
                if target not in assigned_targets:
                    rename_map[col_raw] = target
                    assigned_targets.add(target)
                else:
                    unmatched.append(col_raw)

        for col_raw in df.columns:
            if col_raw in rename_map or col_raw in unmatched:
                continue
            col_clean = str(col_raw).replace(" ", "").lower()
            if "对方" in col_clean or col_clean == "日":
                unmatched.append(col_raw)
                continue

            match_result = process.extractOne(col_clean, list(self.reverse_map.keys()))
            if match_result and match_result[1] >= self.fuzzy_threshold:
                target = self.reverse_map[match_result[0]]
                if target not in assigned_targets:
                    rename_map[col_raw] = target
                    assigned_targets.add(target)
                else:
                    unmatched.append(col_raw)
            else:
                unmatched.append(col_raw)

        df = df.rename(columns=rename_map)

        if "account" not in df.columns:
            if "内容" in df.columns:
                df["account"] = df["内容"].astype(str)
            else:
                df["account"] = "未知科目"

        return df, rename_map, unmatched

    def build_dimensions(self, df: pd.DataFrame, rename_map: dict, excel_header_row: int, sheet_name: str = "") -> pd.DataFrame:
        has_debit = "debit" in df.columns
        has_credit = "credit" in df.columns

        if has_debit or has_credit:
            # 借贷双列（华辰会计凭证）：金额取较大者，方向按哪边非零判
            debit_vals = (
                pd.to_numeric(df["debit"], errors="coerce").fillna(0) if has_debit
                else pd.Series(0.0, index=df.index)
            )
            credit_vals = (
                pd.to_numeric(df["credit"], errors="coerce").fillna(0) if has_credit
                else pd.Series(0.0, index=df.index)
            )
            df["debit"] = debit_vals
            df["credit"] = credit_vals
            df["amount"] = np.maximum(debit_vals, credit_vals)
            df["direction"] = np.where(debit_vals >= credit_vals, "借", "贷")
        elif "价税合计" in df.columns:
            df["amount"] = pd.to_numeric(df["价税合计"], errors="coerce").fillna(0)
            df["direction"] = "借"
        elif "不含税金额" in df.columns:
            df["amount"] = pd.to_numeric(df["不含税金额"], errors="coerce").fillna(0)
            df["direction"] = "借"
        else:
            df["amount"] = 0.0
            df["direction"] = "借"

        df["direction_code"] = np.where(df["direction"] == "借", 1, 0)

        if all(c in df.columns for c in ["年", "月", "日"]):
            y = df["年"].astype(int).astype(str)
            m = df["月"].astype(int).astype(str).str.zfill(2)
            d = df["日"].astype(int).astype(str).str.zfill(2)
            df["date"] = pd.to_datetime(y + "-" + m + "-" + d, errors="coerce")
        elif "发票时间" in df.columns:
            df["date"] = pd.to_datetime(df["发票时间"], errors="coerce")
        elif "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        else:
            df["date"] = pd.NaT

        df["month"] = df["date"].dt.month.fillna(0).astype(int)
        df["day_of_week"] = df["date"].dt.dayofweek.fillna(0).astype(int)

        inv_map = {v: k for k, v in rename_map.items()}
        self.meta_trace = {
            "__excel_source_info": f"表头行:{excel_header_row},工作表:{sheet_name}",
            "amount (金额)": "优先取自借方；无借方则取价税合计→不含税金额",
            "month (月份)": "取自日期字段解析 (0=无效)",
            "day_of_week (星期)": "0=周一,6=周日",
            "direction_code (流向)": "借方记 1",
            "account (科目)": f"取自原始列 [{inv_map.get('account', '内容(替代)')}]"
        }
        df["source_sheet"] = sheet_name
        return df

    def detect_header_row(self, file_path, sheet_name, candidate_rows=[1, 2, 3]):
        for excel_row in candidate_rows:
            pd_header_idx = excel_row - 1
            try:
                df_temp = pd.read_excel(file_path, sheet_name=sheet_name, header=pd_header_idx, nrows=5)
                col_names = [str(c) for c in df_temp.columns]
                for group in self.detect_groups:
                    hit = sum(1 for kw in group if any(kw in c for c in col_names))
                    if hit >= 2:
                        return excel_row
            except Exception:
                continue
        return None

    def load_sheet(self, excel_path, sheet_name: str):
        header_row = self.detect_header_row(excel_path, sheet_name)
        if header_row is None:
            return None

        df_raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row - 1)
        if "摘要" in df_raw.columns:
            df_raw = df_raw[~df_raw["摘要"].astype(str).str.contains("合计|累计|结转")].copy()

        df_norm, rename_log, _ = self.normalize_columns(df_raw)
        if "voucher_id" in df_norm.columns:
            df_norm = df_norm.dropna(subset=["voucher_id"]).copy()

        df_final = self.build_dimensions(df_norm, rename_log, header_row, sheet_name)
        return df_final

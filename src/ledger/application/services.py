import pandas as pd
from ..infrastructure.loaders import ExcelLoader
from ..infrastructure.repository import SQLRepository

class LedgerService:
    def __init__(self):
        self.loader = ExcelLoader()
        self.repository = SQLRepository()
        self.meta_trace = {}

    def process_excel(self, excel_path: str, save_to_db: bool = False) -> tuple[pd.DataFrame, dict]:
        excel_file = pd.ExcelFile(excel_path)
        sheet_list = [s for s in excel_file.sheet_names if s not in self.loader.skip_sheets]
        
        summary_sheets = [s for s in sheet_list if any(kw in s for kw in self.loader.summary_keywords)]
        
        if summary_sheets:
            target_sheet = summary_sheets[0]
            df = self.loader.load_sheet(excel_path, target_sheet)
            if df is None:
                raise RuntimeError(f"总表 [{target_sheet}] 表头探测失败")
        else:
            sheet_data_list = []
            for s in sheet_list:
                sub_df = self.loader.load_sheet(excel_path, s)
                if sub_df is not None:
                    sheet_data_list.append(sub_df)
            if not sheet_data_list:
                raise RuntimeError("所有工作表表头探测失败")
            df = pd.concat(sheet_data_list, ignore_index=True)

        df_final = df[df["amount"] > 0].copy().reset_index(drop=True)
        self.meta_trace = self.loader.meta_trace
        
        if save_to_db:
            self.repository.save_dataframe(df_final)

        info = {
            "raw_count": len(df),
            "clean_count": len(df_final),
            "meta_trace": self.meta_trace
        }
        return df_final, info

    def process_dataframe(self, df: pd.DataFrame, save_to_db: bool = False) -> tuple[pd.DataFrame, dict]:
        """处理 CSV 等已读入的 DataFrame（单表），复用列名模糊匹配与维度构建。"""
        df_norm, rename_map, _ = self.loader.normalize_columns(df)
        if "voucher_id" in df_norm.columns:
            df_norm = df_norm.dropna(subset=["voucher_id"]).copy()

        df_final = self.loader.build_dimensions(df_norm, rename_map, excel_header_row=1, sheet_name="csv")
        df_final = df_final[df_final["amount"] > 0].copy().reset_index(drop=True)
        self.meta_trace = self.loader.meta_trace

        if save_to_db:
            self.repository.save_dataframe(df_final)

        info = {
            "raw_count": len(df),
            "clean_count": len(df_final),
            "meta_trace": self.meta_trace
        }
        return df_final, info

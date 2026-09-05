# 多表数据集（华辰 11 类）的 sheet 类型映射与关联检索配置。
# 与 column_synonyms.py（凭证字段同义词）并列，本文件描述「一张 Excel 里有哪几类表、怎么按类型归类」。

# sheet 名 -> 类型。华辰数据集的 sheet 名规范，精确匹配即可。
SHEET_TYPE_MAP = {
    "会计凭证": "voucher",
    "发票明细": "invoice",
    "银行流水": "bank",
    "采购明细": "purchase",
    "销售明细": "sales",
    "费用明细": "expense",
    "应收账款台账": "receivable",
    "应付账款台账": "payable",
    "供应商台账": "supplier",
    "固定资产台账": "fixed_asset",
    "资产负债表": "financial_statement",
    "利润表": "financial_statement",
    "现金流量表": "financial_statement",
    "所有者权益变动表": "financial_statement",
    "财务报表附注": "financial_statement",
    "风险事项": "risk_items",
    "证据验证映射": "evidence_map",
}
# 「使用说明」「Ground_Truth」有意不映射 —— 元数据/标准答案，不喂给 LLM。

# 可作「证据检索」的表类型：从目标凭证的实体（供应商/客户）出发，在这些表里捞相关行。
EVIDENCE_TYPES = {
    "invoice", "bank", "purchase", "sales", "expense",
    "receivable", "payable", "supplier", "fixed_asset",
}

# 财务报表类：行数少、直接全量喂给 LLM（不按实体筛选）。
STATEMENT_TYPES = {"financial_statement"}

# 风险事项 / 证据验证映射：全量喂给 LLM 作为审计上下文。
META_TYPES = {"risk_items", "evidence_map"}

# 证据表里可作「实体标识」的列，检索时在这些列里找与目标凭证实体值相等的行。
ENTITY_ID_COLUMNS = [
    "供应商编号", "客户编号", "对方编号",
    "供应商名称", "客户名称", "对方名称",
]

# 单个证据表最多喂给 LLM 的行数，防止超长。
MAX_EVIDENCE_ROWS = 50

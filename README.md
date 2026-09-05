# VoucherGuard AI · 智能财务异常审计平台

基于 **DDD 分层架构 + 白盒孤立森林（iForest）异常检测 + 多 Agent 归因 + 可解释证据链穿透** 的财务凭证智能审计系统。

提供 **Web API、React 前端** 两种一致的运行入口，所有入口共享同一套「数据清洗 → 统计模式 → 异常检测 → AI 归因」审计流水线，保证结果一致、可追溯。

---

## 核心特性

| 特性 | 说明 |
|------|------|
| **多格式数据接入** | 支持 Excel（`.xlsx/.xls`）与 CSV；列名模糊匹配、多 Sheet 自动识别、借贷方向编码 |
| **多表数据集** | 自动识别会计凭证 / 发票 / 银行流水 / 采购 / 销售 / 报表等 11 类表，作为证据库喂给 Agent |
| **统计模式建模** | 科目历史均值 + 70% 局部 / 30% 全局贝叶斯收缩平滑 + 偏离倍数量化 |
| **AI 异常检测** | PyOD 孤立森林（iForest 100 棵）+ 多维特征（金额/月份/星期/方向/偏离度）→ 0-100 风险评分 |
| **可解释白盒** | SHAP 特征贡献瀑布图 + iTree 平均切分深度拓扑曲线 + 人类可读诊断文本 |
| **多 Agent 归因** | planner + 凭证/发票/银行/报表/供应商 5 个领域专家，通过 function calling 调用确定性工具 |
| **双护栏** | 输入防提示词注入 + 输出防过度定性/越界表述 |
| **人类把关（HITL）** | 归因报告以 draft 状态生成，需人工确认/驳回后才计入审计发现 |
| **项目与共享记忆** | 同一项目可追加多个数据集合并分析，并共享 Agent 记忆与审计轨迹 |
| **自定义大模型** | DeepSeek API Key / Base URL / Model 可从前端「系统设置」页自行填写，保存即生效 |
| **报告导出** | 凭证清单 CSV 导出 + 可解释分析报告导出 |

---

## 系统架构

```
前端 React 18 (Ant Design + ECharts)
        │  /api（Vite 代理 → FastAPI:8000）
        ▼
FastAPI 后端（src/app.py）
  ├─ 项目/数据集/上传（project + datasets）
  ├─ 检测流水线（ledger → pattern → anomaly → reporting）
  └─ Agent 归因（planner → 领域专家 → 汇总报告）
        │
        ▼
确定性工具层 + 双护栏 + 追加式审计轨迹
        │
        ▼
数据层：SQLite（生产建议 PostgreSQL + pgvector）
```

### Agent 编排流程

```
输入护栏（防注入）
   → planner（按风险类型派发专家子集）
        → 凭证专家 / 发票专家 / 银行专家 / 报表专家 / 供应商专家
             → 各自调用确定性工具（三流比对/发票查重/供应商趋势/报表勾稽等）
   → 汇总生成八段式归因报告
   → 输出护栏（防越界）
   → HITL 人工确认/驳回 → 追加审计轨迹
```

---

## 快速开始

### ① 后端（端口 8000）

```bash
pip install -r requirements.txt
# 可选：复制 .env.example 为 .env 并填写 DeepSeek 配置
python src/app.py
```

Swagger 文档：http://localhost:8000/docs

> 也可以在启动后端后，直接在前端「系统设置」页填写 DeepSeek API Key，无需修改 `.env`。

### ② 前端（端口 5173）

```bash
cd frontend
npm install
npm run dev
```

浏览器访问：http://localhost:5173/

进入「账本上传」页，选择 `data/raw/test_data.xlsx` 或任意 CSV 即可端到端体验完整审计流程。

---

## 四阶段审计流水线

```
阶段1 数据清洗与映射
   │  Excel/CSV → 列名模糊匹配 → 借贷编码 → 月份/星期/窗口期维度
   ▼
阶段2 统计模式分析
   │  按科目聚合历史均值 + 70%局部·30%全局收缩平滑 → 偏离倍数
   ▼
阶段3 iForest 孤立森林检测
   │  100 棵 iTree 多维拓扑切分 → 异常分 → 0-100 风险评分 → 诊断文本
   ▼
阶段4 AI 归因 + 证据链穿透
   │  planner 派发领域专家 → 确定性工具验证 → 八段式报告 → 人工确认
   ▼
交付物：审计发现（可追溯、可确认/驳回）
```

---

## 技术栈

**后端：** Python 3.11+ · FastAPI · Uvicorn · SQLAlchemy + SQLite · Pandas/NumPy · PyOD (iForest) · openpyxl · fuzzywuzzy/Levenshtein · OpenAI SDK（DeepSeek 兼容）

**前端：** React 18 (TypeScript) · Vite 5 · Ant Design 5 · ECharts 5 · React Router 6 · Zustand · Lucide Icons

---

## 目录结构

```
fintech/
├── src/app.py                     # FastAPI 入口（上传/项目/凭证/统计/Agent 归因/设置）
├── config/                        # 列名同义词、表类型映射
├── data/
│   ├── raw/test_data.xlsx         # 内置测试账本
│   └── output/                    # 报告输出目录
├── src/
│   ├── ledger/                    # ① 账本与凭证（Excel/CSV 清洗、维度编码、入库）
│   ├── pattern/                   # ② 统计模式（贝叶斯收缩、偏离倍数）
│   ├── anomaly/                   # ③ 异常检测（iForest + 评分映射 + tree_trace）
│   ├── investigation/             # ④ 审计调查域（骨架）
│   ├── reporting/                 # ⑤ 报告输出（Excel 底稿）
│   ├── retrieval/                 # ⑥ 语义检索域（预留 RAG）
│   └── agent/                     # ⑦ 多 Agent 归因
│       ├── application/
│       │   ├── services.py        #    planner → 专家 → 汇总 编排
│       │   ├── specialists.py     #    5 个领域专家 + 工具白名单
│       │   └── payload.py         #    风险载荷与证据构造
│       ├── infrastructure/
│       │   ├── llm.py             #    DeepSeek 客户端（支持 function calling）
│       │   ├── tools.py           #    确定性审计工具层
│       │   └── guardrails.py      #    输入/输出双护栏
│       └── prompts/               #    skill / 证据分类 / 报告模板 / 示例
└── frontend/
    └── src/
        ├── App.tsx                # 路由
        ├── components/            # MainLayout / ProjectSwitcher
        ├── store/project.ts       # 项目状态（Zustand）
        └── pages/
            ├── Dashboard.tsx      # 总览仪表盘
            ├── Upload.tsx         # 账本上传（Excel/CSV + 追加/替换）
            ├── Vouchers.tsx       # 凭证风险清单（搜索/筛选/导出/穿透）
            ├── Explainability.tsx # 可解释分析
            ├── RiskAttribution.tsx# Agent 归因 + 专家过程可视化 + HITL
            └── Settings.tsx       # DeepSeek API 用户自定义配置
```

---

## 项目（Project）与共享记忆

- 顶部「项目切换器」可新建/切换项目。
- 上传时可选「追加为多数据集（合并分析）」或「替换项目数据（单数据集）」。
- 同一项目内的 Agent 记忆与审计发现按项目隔离、共享，跨风险复用已验证结论。

---

## License

内部项目 © VoucherGuard AI Team

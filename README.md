# VoucherGuard AI · 智能财务异常审计平台

基于 **DDD 分层架构 + 白盒孤立森林 (iForest) 异常检测 + 可解释证据链穿透** 的财务凭证智能审计系统。

提供 **Web API、React 前端** 两种一致的运行入口，所有入口共享同一套核心 4 阶段审计流水线，保证结果 100% 一致。

---

## 🏆 核心特性

| 特性 | 说明 |
|------|------|
| **数据清洗容错** | Excel 列名模糊匹配（借方金额/金额/借方等字段自动映射）、多 Sheet 自动识别、借贷方向编码 |
| **统计模式建模** | 会计科目历史均值计算 + 70% 局部 / 30% 全局贝叶斯收缩平滑 + 偏离倍数量化 |
| **AI 异常检测** | PyOD 孤立森林 (iForest 100 棵) + 多维特征（金额/月份/星期/偏离度/流向）→ 0-100 风险评分 |
| **可解释白盒** | SHAP 特征贡献瀑布图 + iTree 平均切分深度拓扑曲线 + 人类可读诊断文本（金额偏离/非工作日/年末突击）|
| **报告导出** | 双 Sheet Excel 透明审计底稿（异常清单 + 统计验证）|
| **SQLite 持久化** | SQLAlchemy 本地数据库，可追溯、可增量分析 |
| **多 Agent 骨架** | 包含 Agent 状态机 / 语义检索 / 多源证据（发票/合同/银行流水）子域骨架 |

---

## 🗂️ 项目架构

```
fintech/
├── src/app.py              # Web API (FastAPI) 入口     → http://localhost:8000
│
├── config/column_synonyms.py    # Excel 字段字典
├── data/
│   ├── raw/test_data.xlsx       # 内置测试账本（242 条凭证）
│   └── output/                  # 报告输出目录（已 gitignore）
│
├── src/                    # ========== 后端 DDD 分层（Interface / Application / Domain / Infrastructure）==========
│   ├── ledger/             # ① 账本与凭证基础域（数据清洗、维度编码、SQLite 入库）
│   ├── pattern/            # ② 统计模式域（科目均值、贝叶斯收缩、偏离倍数）
│   ├── anomaly/            # ③ 异常检测域（iForest 核心 AI + 评分映射）
│   ├── investigation/      # ④ 审计调查域（舞弊假设、证据排序）
│   ├── reporting/          # ⑤ 报告输出域（双 Sheet Excel 审计底稿）
│   ├── agent/              # ⑥ 多智能体审计域（LangGraph 风格状态机）
│   ├── retrieval/          # ⑦ 语义检索域（RAG 召回）
│   └── evidence/           # ⑧ 多源证据域（凭证/发票/合同/银行流水）
│
└── frontend/               # ========== 前端 (React 18 + Vite 5 + Ant Design 5 + ECharts) ==========
    └── src/
        ├── App.tsx                 # 4 条业务路由
        ├── components/MainLayout.tsx   # 侧边栏 + 顶栏主布局
        └── pages/
            ├── Dashboard.tsx         📊 4 KPI + 月度趋势 + 风险等级饼图
            ├── Upload.tsx            📤 拖拽上传 + 实时进度 + 格式校验
            ├── Vouchers.tsx          📒 9 列风险清单 + 搜索/筛选/排序
            └── Explainability.tsx    🔍 SHAP 瀑布 + iForest 深度曲线 + 诊断说明
```

---

## 🚀 快速开始

### Web 本地部署（推荐）

**① 启动后端 API (端口 8000)**
```bash
pip install -r requirements.txt
python src/app.py
```
Swagger 文档：http://localhost:8000/docs

**② 启动前端网站 (端口 5173)**
```bash
cd frontend
npm install
npm run dev
```
浏览器访问：http://localhost:5173/
进入「账本上传」页面，选择 `data/raw/test_data.xlsx` 即可端到端体验完整审计流程。

---

## 🔬 四阶段审计流水线

```
阶段1 数据清洗与映射
   │  Excel → 列名模糊匹配 → 借贷编码 → 月份/星期/节假日/窗口期维度
   ▼
阶段2 统计模式分析
   │  按科目聚合历史均值 + 70%局部·30%全局收缩平滑 → 偏离倍数
   ▼
阶段3 iForest 孤立森林检测
   │  100 棵 iTree 多维拓扑切分 → 异常分 → 0-100 风险评分 → 诊断文本
   ▼
阶段4 Top 5 高危穿透 + Excel 报告
   │  Top N 证据链 + 双 Sheet 审计底稿（异常清单 / 统计验证）
   ▼
  交付物
```

---

## 📦 技术栈

**后端：** Python 3.11+ · FastAPI · Uvicorn · SQLAlchemy + SQLite · Pandas/NumPy · PyOD (iForest) · openpyxl · fuzzywuzzy/Levenshtein

**前端：** React 18 (TypeScript) · Vite 5 · Ant Design 5 · ECharts 5 · React Router 6 · Zustand · Lucide Icons

**打包：** PyInstaller → Windows 单文件 EXE

---

## 📝 License

内部项目 © VoucherGuard AI Team

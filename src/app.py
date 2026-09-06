from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import pandas as pd
import os
import shutil
import uuid
import json
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from src.ledger.application.services import LedgerService
from src.ledger.infrastructure.multi_table import load_multi_table
from src.pattern.application.services import PatternService
from src.anomaly.application.services import AnomalyService
from src.reporting.application.services import ReportingService
from src.agent.application.services import AttributionAgent
from src.agent.application.payload import build_risk_payload, normalize_voucher_id
from src.agent.infrastructure.guardrails import detect_prompt_injection, validate_output

load_dotenv()

# DeepSeek 大模型配置（用户可从前端设置页动态修改，初始取自 .env）
LLM_SETTINGS = {
    "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
    "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
}

app = FastAPI(title="VoucherGuard AI API")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
ledger_service = LedgerService()
pattern_service = PatternService(alpha=0.7)
anomaly_service = AnomalyService(contamination=0.03, n_estimators=100)
reporting_service = ReportingService()

# 项目级数据缓存（演示版使用进程内存；生产环境建议替换为数据库/对象存储）
DEFAULT_PROJECT_ID = "default"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clean_records(df: pd.DataFrame) -> list[dict]:
    """把 DataFrame 转成 JSON 安全的记录列表，清洗 NaN 与时间戳。"""
    records = []
    for _, r in df.iterrows():
        rec = {}
        for col, val in r.items():
            if val is None:
                continue
            try:
                if pd.isna(val):
                    continue
            except (TypeError, ValueError):
                pass
            if isinstance(val, pd.Timestamp):
                val = val.strftime("%Y-%m-%d")
            elif isinstance(val, float):
                val = round(val, 2)
            elif hasattr(val, "item"):
                try:
                    val = val.item()
                except Exception:
                    pass
            rec[str(col)] = val
        records.append(rec)
    return records


def _new_project(project_id: str, name: str) -> dict:
    now = _now()
    return {
        "id": project_id,
        "name": name,
        "created_at": now,
        "updated_at": now,
        "datasets": [],
        "last_result": None,
        "last_stats": None,
        "tree_trace": None,
        "prep_info": None,
        "last_file": None,
        "tables": {},
        "agent_memory": [],
    }


PROJECTS: dict[str, dict] = {
    DEFAULT_PROJECT_ID: _new_project(DEFAULT_PROJECT_ID, "默认项目")
}
ACTIVE_PROJECT_ID = DEFAULT_PROJECT_ID

# 兼容旧接口语义：默认指向当前激活项目
CACHE = PROJECTS[DEFAULT_PROJECT_ID]

attribution_agent = AttributionAgent()

# P2：审计 finding（draft → confirmed/rejected）与 P5：追加式审计轨迹（演示版内存，生产换库）
FINDINGS: dict[str, dict] = {}
AUDIT_TRAIL: list[dict] = []


def _project_summary(project: dict) -> dict:
    df = project.get("last_result")
    return {
        "id": project["id"],
        "name": project["name"],
        "created_at": project["created_at"],
        "updated_at": project["updated_at"],
        "dataset_count": len(project.get("datasets") or []),
        "memory_count": len(project.get("agent_memory") or []),
        "last_file": project.get("last_file"),
        "total_count": 0 if df is None else int(len(df)),
        "anomaly_count": 0 if df is None else int(df["是否异常"].sum()),
        "avg_risk_score": 0 if df is None or df.empty else float(df["风险评分"].mean()),
    }


def _get_project(project_id: Optional[str] = None) -> dict:
    pid = project_id or ACTIVE_PROJECT_ID or DEFAULT_PROJECT_ID
    project = PROJECTS.get(pid)
    if project is None:
        raise HTTPException(status_code=404, detail=f"未找到项目 {pid}")
    return project


def _set_active_project(project_id: str) -> dict:
    global ACTIVE_PROJECT_ID, CACHE
    project = _get_project(project_id)
    ACTIVE_PROJECT_ID = project["id"]
    CACHE = project
    return project


def _load_dataset(temp_path: str, filename: str) -> dict:
    """按文件类型加载：CSV 走单表 DataFrame 清洗，Excel 优先多表加载。"""
    if filename.lower().endswith(".csv"):
        df_raw = pd.read_csv(temp_path)
        tables = {}
        df_clean, prep_info = ledger_service.process_dataframe(df_raw, save_to_db=True)
    else:
        tables = load_multi_table(temp_path)
        if "会计凭证" in tables:
            df_clean = tables["会计凭证"]
            df_clean = df_clean[df_clean["amount"] > 0].copy().reset_index(drop=True)
            prep_info = {
                "clean_count": len(df_clean),
                "meta_trace": {"多表加载": list(tables.keys())},
            }
        else:
            tables = {}
            df_clean, prep_info = ledger_service.process_excel(temp_path, save_to_db=True)

    df_clean = df_clean.copy()
    df_clean["project_dataset"] = filename
    return {
        "id": uuid.uuid4().hex,
        "filename": filename,
        "uploaded_at": _now(),
        "df_clean": df_clean,
        "tables": tables,
        "prep_info": prep_info,
    }


def _merge_tables(datasets: list[dict]) -> dict[str, pd.DataFrame]:
    merged: dict[str, list[pd.DataFrame]] = {}
    for dataset in datasets:
        for sheet, df in (dataset.get("tables") or {}).items():
            merged.setdefault(sheet, []).append(df)
    return {
        sheet: pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
        for sheet, frames in merged.items()
    }


def _reprocess_project(project: dict) -> None:
    datasets = project.get("datasets") or []
    if not datasets:
        project.update({
            "last_result": None, "last_stats": None, "tree_trace": None,
            "prep_info": None, "last_file": None, "tables": {},
        })
        return

    df_clean = pd.concat([d["df_clean"] for d in datasets], ignore_index=True)
    df_featured = pattern_service.analyze_patterns(df_clean)
    project["last_stats"] = pattern_service.acc_stats

    target_features = ["amount", "month", "day_of_week", "direction_code", "amount_deviation_ratio"]
    project["last_result"] = anomaly_service.detect_anomalies(df_featured, feature_cols=target_features)
    project["tree_trace"] = anomaly_service.tree_trace
    project["tables"] = _merge_tables(datasets)
    project["prep_info"] = {
        "clean_count": int(len(df_clean)),
        "dataset_count": len(datasets),
        "meta_trace": {d["filename"]: d.get("prep_info", {}).get("meta_trace", {}) for d in datasets},
    }
    project["last_file"] = datasets[-1]["filename"]
    project["updated_at"] = _now()


class LLMSettingsRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


def _llm_settings_payload() -> dict:
    return {
        "api_key_set": bool(LLM_SETTINGS["api_key"]),
        "base_url": LLM_SETTINGS["base_url"],
        "model": LLM_SETTINGS["model"],
    }


@app.get("/api/settings/llm")
async def get_llm_settings():
    return _llm_settings_payload()


@app.post("/api/settings/llm")
async def update_llm_settings(req: LLMSettingsRequest):
    if req.api_key and req.api_key.strip():
        LLM_SETTINGS["api_key"] = req.api_key.strip()
    if req.base_url and req.base_url.strip():
        LLM_SETTINGS["base_url"] = req.base_url.strip()
    if req.model and req.model.strip():
        LLM_SETTINGS["model"] = req.model.strip()

    attribution_agent.llm.configure(
        api_key=LLM_SETTINGS["api_key"] or None,
        base_url=LLM_SETTINGS["base_url"] or None,
        model=LLM_SETTINGS["model"] or None,
    )
    return _llm_settings_payload()


class ProjectCreateRequest(BaseModel):
    name: str


class ProjectActivateRequest(BaseModel):
    project_id: str


@app.get("/api/projects")
async def list_projects():
    return {
        "active_project_id": ACTIVE_PROJECT_ID,
        "projects": [_project_summary(p) for p in PROJECTS.values()],
    }


@app.post("/api/projects")
async def create_project(req: ProjectCreateRequest):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="项目名称不能为空")
    project_id = uuid.uuid4().hex[:12]
    PROJECTS[project_id] = _new_project(project_id, name)
    project = _set_active_project(project_id)
    return _project_summary(project)


@app.post("/api/projects/active")
async def activate_project(req: ProjectActivateRequest):
    project = _set_active_project(req.project_id)
    return _project_summary(project)


@app.post("/api/upload")
async def upload_ledger(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    append: bool = Form(True),
):
    if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="仅支持 Excel（.xlsx/.xls）或 CSV 文件")

    project = _get_project(project_id)
    _set_active_project(project["id"])

    # 上传文件持久化保存到 data/raw，与内置 test_data.xlsx 同目录，便于复用与追溯
    raw_dir = "data/raw"
    os.makedirs(raw_dir, exist_ok=True)
    save_path = os.path.join(raw_dir, file.filename)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        dataset = _load_dataset(save_path, file.filename)
        if not append:
            project["datasets"] = []
            project["agent_memory"] = []
        project["datasets"].append(dataset)
        _reprocess_project(project)

        df_result = project["last_result"]
        prep_info = project["prep_info"] or {}

        return {
            "status": "success",
            "project": _project_summary(project),
            "summary": {
                "total_count": prep_info["clean_count"],
                "anomaly_count": int(df_result["是否异常"].sum()),
                "avg_risk_score": float(df_result["风险评分"].mean())
            },
            "table_types": list(project.get("tables", {}).keys()),
            "meta_trace": prep_info.get("meta_trace", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vouchers")
async def get_vouchers(limit: int = 50, risk_min: float = 0, project_id: Optional[str] = None):
    project = _get_project(project_id)
    if project["last_result"] is None:
        return []

    df = project["last_result"]
    filtered_df = df[df["风险评分"] >= risk_min].head(limit)

    return _clean_records(filtered_df)

@app.get("/api/stats/dashboard")
async def get_dashboard_stats(project_id: Optional[str] = None):
    project = _get_project(project_id)
    if project["last_result"] is None:
        return {
            "total_vouchers": 0,
            "anomaly_vouchers": 0,
            "avg_risk_score": 0,
            "critical_vouchers": 0,
            "risk_distribution": {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
        }

    df = project["last_result"]
    total = len(df)
    anomalies = int(df["是否异常"].sum())
    avg_score = float(df["风险评分"].mean())
    critical = int((df["风险评分"] >= 90).sum())

    dist = {
        "Low": int((df["风险评分"] < 30).sum()),
        "Medium": int(((df["风险评分"] >= 30) & (df["风险评分"] < 70)).sum()),
        "High": int(((df["风险评分"] >= 70) & (df["风险评分"] < 90)).sum()),
        "Critical": critical
    }

    return {
        "total_vouchers": total,
        "anomaly_vouchers": anomalies,
        "avg_risk_score": avg_score,
        "critical_vouchers": critical,
        "risk_distribution": dist
    }

@app.get("/api/analytics/tree-trace")
async def get_tree_trace(project_id: Optional[str] = None):
    project = _get_project(project_id)
    return project.get("tree_trace") or {}


class AttributionRequest(BaseModel):
    voucher_id: Optional[str] = None
    project_id: Optional[str] = None


def _prepare_attribution(req: Optional[AttributionRequest]):
    project = _get_project(req.project_id if req else None)
    _set_active_project(project["id"])
    if project["last_result"] is None:
        raise HTTPException(status_code=400, detail="尚未上传账本数据，请先上传 Excel 后再生成归因报告")

    df = project["last_result"]
    voucher_id = req.voucher_id if req else None

    if voucher_id:
        target = normalize_voucher_id(voucher_id)
        matched = df[df["voucher_id"].apply(normalize_voucher_id) == target]
        if matched.empty:
            raise HTTPException(status_code=404, detail=f"未找到凭证 {target}")
        row = matched.iloc[0]
    else:
        row = df.iloc[0]  # df 已按风险评分降序，首行即最高风险

    tables = project.get("tables") or {}
    payload = build_risk_payload(row.to_dict(), tables)
    payload["project"] = {
        "id": project["id"],
        "name": project["name"],
        "datasets": [d["filename"] for d in project.get("datasets", [])],
    }
    payload["project_memory"] = project.get("agent_memory", [])[-5:]

    # P3 输入护栏：拦截凭证摘要/供应商名等字段中的提示词注入
    injection = detect_prompt_injection(payload)
    if injection:
        raise HTTPException(status_code=400, detail=f"输入护栏拦截：{injection}")

    return project, row, payload


@app.post("/api/agent/attribution")
async def agent_attribution(req: Optional[AttributionRequest] = None):
    project, row, payload = _prepare_attribution(req)

    try:
        result = attribution_agent.analyze_with_trace(payload)
        report = result["report"]
        trace = result.get("steps", [])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"大模型调用失败：{e}")

    # P3 输出护栏：拦截过度定性 / 越界表述
    violations = validate_output(report)
    if violations:
        report = (
            "> ⚠️ 输出护栏提示：检测到以下越界表述，请人工复核——"
            + "、".join(violations)
            + "\n\n"
            + report
        )

    # P5 追加式审计轨迹（只追加，不删除）
    AUDIT_TRAIL.append({
        "time": _now(),
        "project_id": project["id"],
        "voucher_id": normalize_voucher_id(row.get("voucher_id")),
        "specialists": result.get("specialists", []),
        "steps": trace,
        "violations": violations,
    })

    # 项目级共享记忆（保留旧字段，供后续归因复用）
    memory_item = {
        "time": _now(),
        "voucher_id": normalize_voucher_id(row.get("voucher_id")),
        "risk_score": float(row.get("风险评分") or 0),
        "summary": report[:800],
    }
    project.setdefault("agent_memory", []).append(memory_item)
    project["agent_memory"] = project["agent_memory"][-20:]
    project["updated_at"] = _now()

    # P2 创建 finding（draft 状态，等待人工确认）
    finding_id = uuid.uuid4().hex[:12]
    FINDINGS[finding_id] = {
        "id": finding_id,
        "project_id": project["id"],
        "voucher_id": normalize_voucher_id(row.get("voucher_id")),
        "risk_score": float(row.get("风险评分") or 0),
        "report": report,
        "status": "draft",
        "created_at": _now(),
        "updated_at": _now(),
    }

    return {
        "project_id": project["id"],
        "project_name": project["name"],
        "voucher_id": normalize_voucher_id(row.get("voucher_id")),
        "risk_score": float(row.get("风险评分") or 0),
        "finding_id": finding_id,
        "status": "draft",
        "memory_count": len(project.get("agent_memory", [])),
        "specialists": result.get("specialists", []),
        "steps": trace,
        "violations": violations,
        "report": report,
    }


@app.post("/api/agent/attribution/stream")
async def agent_attribution_stream(req: Optional[AttributionRequest] = None):
    project, row, payload = _prepare_attribution(req)

    def event_stream():
        final_report = ""
        final_steps: list[dict] = []
        final_specialists: list[str] = []
        try:
            for event in attribution_agent.analyze_stream(payload):
                if event.get("type") == "report":
                    final_report = event.get("report", "")
                    final_steps = event.get("steps", [])
                    final_specialists = event.get("specialists", [])
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            return

        violations = validate_output(final_report)
        if violations:
            final_report = (
                "> ⚠️ 输出护栏提示：检测到以下越界表述，请人工复核——"
                + "、".join(violations)
                + "\n\n"
                + final_report
            )

        AUDIT_TRAIL.append({
            "time": _now(),
            "project_id": project["id"],
            "voucher_id": normalize_voucher_id(row.get("voucher_id")),
            "specialists": final_specialists,
            "steps": final_steps,
            "violations": violations,
        })

        memory_item = {
            "time": _now(),
            "voucher_id": normalize_voucher_id(row.get("voucher_id")),
            "risk_score": float(row.get("风险评分") or 0),
            "summary": final_report[:800],
        }
        project.setdefault("agent_memory", []).append(memory_item)
        project["agent_memory"] = project["agent_memory"][-20:]
        project["updated_at"] = _now()

        finding_id = uuid.uuid4().hex[:12]
        FINDINGS[finding_id] = {
            "id": finding_id,
            "project_id": project["id"],
            "voucher_id": normalize_voucher_id(row.get("voucher_id")),
            "risk_score": float(row.get("风险评分") or 0),
            "report": final_report,
            "status": "draft",
            "created_at": _now(),
            "updated_at": _now(),
        }

        done_payload = {
            "type": "done",
            "finding_id": finding_id,
            "status": "draft",
            "project_id": project["id"],
            "project_name": project["name"],
            "voucher_id": normalize_voucher_id(row.get("voucher_id")),
            "risk_score": float(row.get("风险评分") or 0),
            "violations": violations,
            "report": final_report,
            "steps": final_steps,
            "specialists": final_specialists,
        }
        yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class FindingStatusRequest(BaseModel):
    status: str


@app.get("/api/findings")
async def list_findings(project_id: Optional[str] = None):
    pid = project_id or ACTIVE_PROJECT_ID or DEFAULT_PROJECT_ID
    items = [f for f in FINDINGS.values() if f["project_id"] == pid]
    return {"findings": items}


@app.post("/api/findings/{finding_id}/status")
async def update_finding_status(finding_id: str, req: FindingStatusRequest):
    finding = FINDINGS.get(finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail=f"未找到 finding {finding_id}")
    if req.status not in ("confirmed", "rejected", "draft"):
        raise HTTPException(status_code=400, detail="status 只能是 confirmed/rejected/draft")

    finding["status"] = req.status
    finding["updated_at"] = _now()
    AUDIT_TRAIL.append({
        "time": _now(),
        "action": "finding_status",
        "finding_id": finding_id,
        "status": req.status,
        "project_id": finding["project_id"],
    })
    return finding


# ---------- 前端静态资源托管（生产部署）----------
# 若存在 React 构建产物，则挂载并支持 SPA 路由回退；
# 否则保持纯 API 模式（本地开发时由 Vite dev server 代理 /api）。
FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))

if os.path.isdir(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        candidate = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
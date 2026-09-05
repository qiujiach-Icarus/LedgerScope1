from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd
import os
import shutil
from typing import List, Optional

from src.ledger.application.services import LedgerService
from src.pattern.application.services import PatternService
from src.anomaly.application.services import AnomalyService
from src.reporting.application.services import ReportingService

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

# 全局数据缓存（实际生产应使用数据库）
CACHE = {
    "last_result": None,
    "last_stats": None,
    "prep_info": None
}

@app.post("/api/upload")
async def upload_ledger(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    temp_path = f"data/raw/temp_{file.filename}"
    os.makedirs("data/raw", exist_ok=True)
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # 1. 预处理
        df_clean, info = ledger_service.process_excel(temp_path, save_to_db=True)
        CACHE["prep_info"] = info
        
        # 2. 统计模式
        df_featured = pattern_service.analyze_patterns(df_clean)
        CACHE["last_stats"] = pattern_service.acc_stats
        
        # 3. 异常检测
        target_features = ["amount", "month", "day_of_week", "direction_code", "amount_deviation_ratio"]
        df_result = anomaly_service.detect_anomalies(df_featured, feature_cols=target_features)
        CACHE["last_result"] = df_result
        
        return {
            "status": "success",
            "summary": {
                "total_count": info["clean_count"],
                "anomaly_count": int(df_result["是否异常"].sum()),
                "avg_risk_score": float(df_result["风险评分"].mean())
            },
            "meta_trace": info["meta_trace"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/api/vouchers")
async def get_vouchers(limit: int = 50, risk_min: float = 0):
    if CACHE["last_result"] is None:
        return []
    
    df = CACHE["last_result"]
    filtered_df = df[df["风险评分"] >= risk_min].head(limit)
    
    return filtered_df.to_dict(orient="records")

@app.get("/api/stats/dashboard")
async def get_dashboard_stats():
    if CACHE["last_result"] is None:
        return {
            "total_vouchers": 0,
            "anomaly_vouchers": 0,
            "avg_risk_score": 0,
            "critical_vouchers": 0,
            "risk_distribution": {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
        }
    
    df = CACHE["last_result"]
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
async def get_tree_trace():
    return anomaly_service.tree_trace

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

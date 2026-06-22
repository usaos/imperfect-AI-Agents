from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import io
import json
from database import db
from config import config

app = FastAPI(title="imperfect API", description="Agent Imperfection Protocol v3.1", version="3.1.0")

# CORS 支持，前端可直接调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 简易API鉴权
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)):
    if config.API_KEY and api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True

# 请求模型
class ScarLogRequest(BaseModel):
    task: str
    failure_action: Optional[str] = "Unknown"
    failure_error: str
    reflection_analysis: str
    corrected_action: str
    uncertainty_score: float = 0.5
    source_platform: str = "api"
    pre_condition: str = ""
    tags: str = ""
    agent_id: str = "anonymous"
    failure_trace: str = ""

class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    min_quality: Optional[str] = None

@app.get("/")
async def root():
    return {"name": "imperfect", "version": "3.1.0", "status": "running"}

@app.post("/api/scars/log", dependencies=[Depends(verify_api_key)])
async def log_scar(req: ScarLogRequest):
    scar_id = db.add_scar(
        task=req.task,
        failure_action=req.failure_action,
        failure_error=req.failure_error,
        reflection_analysis=req.reflection_analysis,
        corrected_action=req.corrected_action,
        uncertainty_score=req.uncertainty_score,
        source_platform=req.source_platform,
        pre_condition=req.pre_condition,
        tags=req.tags,
        agent_id=req.agent_id,
        failure_trace=req.failure_trace
    )
    if scar_id == -1:
        raise HTTPException(status_code=429, detail="Duplicate submission detected. Scar rejected.")
    return {"status": "success", "scar_id": scar_id, "credit_added": 5}

@app.post("/api/scars/search", dependencies=[Depends(verify_api_key)])
async def search_scars(req: SearchRequest):
    results = db.search_scars(req.query, req.limit, req.min_quality)
    return {"count": len(results), "results": results}

@app.get("/api/stats", dependencies=[Depends(verify_api_key)])
async def get_stats():
    return db.get_stats()

@app.get("/api/scars/export_dpo", dependencies=[Depends(verify_api_key)])
async def export_dpo(tags: str = "", min_quality: str = "complete", download: bool = False, api_key: str = ""):
    # 支持URL参数传递api_key（用于浏览器直接下载）
    if config.API_KEY and api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    data = db.export_dpo(tags, min_quality)
    if not download:
        return {"total": len(data), "data": data}
    
    # 流式下载JSONL文件
    def generate():
        for item in data:
            yield json.dumps(item, ensure_ascii=False) + "\n"
    
    return StreamingResponse(
        generate(),
        media_type="application/jsonl",
        headers={"Content-Disposition": f"attachment; filename=imperfect_dpo_dataset.jsonl"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

"""FastAPI 应用入口 — 路由、CORS、静态文件、SSE。

DDD 阶段核心产物：前端驱动的 API 端点实现。
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from panel_studio.config import HOST, PORT, DEBUG
from panel_studio.core import PanelCore
from panel_studio.db import PanelDB
from panel_studio.sse import SSEManager

logger = logging.getLogger(__name__)

# ============================================================
# 应用初始化
# ============================================================

app = FastAPI(
    title="AI Panel Studio",
    description="AI圆桌讨论演播厅",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局实例
db = PanelDB()
sse = SSEManager()
core = PanelCore(db=db, sse=sse)

# 静态文件
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ============================================================
# 页面路由
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index_page():
    """首页。"""
    html_file = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.get("/studio/{discussion_id}", response_class=HTMLResponse)
async def studio_page(discussion_id: str):
    """演播厅页面。"""
    html_file = STATIC_DIR / "studio.html"
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


# ============================================================
# API 路由
# ============================================================

@app.get("/api/discussions")
async def list_discussions(status: str | None = None):
    """列出讨论。"""
    return core.list_discussions(status=status)


@app.post("/api/discussions")
async def create_discussion(request: Request):
    """创建讨论。"""
    body = await request.json()
    topic = body.get("topic", "").strip()
    expert_count = body.get("expert_count", 4)

    if not topic:
        raise HTTPException(status_code=400, detail="话题不能为空")
    if not (2 <= expert_count <= 8):
        raise HTTPException(status_code=400, detail="专家人数必须在2-8之间")

    return core.create_discussion(topic, expert_count)


@app.get("/api/discussions/{discussion_id}")
async def get_discussion(discussion_id: str):
    """获取讨论详情。"""
    result = core.get_discussion(discussion_id)
    if not result:
        raise HTTPException(status_code=404, detail="讨论不存在")
    return result


@app.post("/api/discussions/{discussion_id}/panelists/generate")
async def generate_panelists(discussion_id: str):
    """AI 生成嘉宾阵容。"""
    result = await core.generate_panelists_for_discussion(discussion_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "生成失败"))
    return result


@app.post("/api/discussions/{discussion_id}/confirm")
async def confirm_panelists(discussion_id: str):
    """确认嘉宾，进入演播厅。"""
    result = await core.confirm_and_start(discussion_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "确认失败"))
    return result


@app.post("/api/discussions/{discussion_id}/start")
async def start_discussion(discussion_id: str):
    """启动讨论引擎。"""
    # 异步启动，不阻塞请求
    asyncio.create_task(core.run_discussion(discussion_id))
    return {"ok": True, "message": "讨论引擎已启动"}


@app.post("/api/discussions/{discussion_id}/stop")
async def stop_discussion(discussion_id: str, request: Request):
    """结束讨论。"""
    conclusion = None
    try:
        if request.headers.get("content-type") == "application/json":
            body = await request.json()
            conclusion = body.get("conclusion")
    except Exception:
        pass  # 无 body 或非 JSON 时忽略
    result = await core.stop_discussion(discussion_id, conclusion)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "结束失败"))
    return result


@app.get("/api/discussions/{discussion_id}/events")
async def sse_events(discussion_id: str):
    """SSE 事件流。"""
    queue = sse.subscribe(discussion_id)

    # 发送初始状态
    disc_data = core.get_discussion(discussion_id)
    if disc_data:
        from panel_studio.sse import format_sse
        init_event = format_sse("init", disc_data)

        async def generate():
            yield init_event
            async for event in sse.stream(discussion_id, queue):
                yield event

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    raise HTTPException(status_code=404, detail="讨论不存在")


# ============================================================
# 启动入口
# ============================================================

def run():
    """启动服务。"""
    import uvicorn
    uvicorn.run(
        "panel_studio.app:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
    )


if __name__ == "__main__":
    run()

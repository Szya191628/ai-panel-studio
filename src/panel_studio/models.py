"""数据模型 — Pydantic 模型定义，驱动 API 契约与数据库映射。

SDD 阶段核心产物：所有实体在此定义，schema.py 和 db.py 对齐此模型。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ============================================================
# 请求/响应模型 (API Contract)
# ============================================================


class CreateDiscussionRequest(BaseModel):
    """创建讨论的请求体。"""
    topic: str = Field(..., min_length=1, max_length=200, description="讨论话题")
    expert_count: int = Field(default=4, ge=2, le=8, description="专家人数（不含主持人）")


class GeneratePanelistsRequest(BaseModel):
    """触发 AI 生成嘉宾阵容。"""
    pass  # 无需额外参数，话题已存在讨论中


class ConfirmPanelistsRequest(BaseModel):
    """用户确认嘉宾阵容，进入演播厅。"""
    pass


class StartDiscussionRequest(BaseModel):
    """开始讨论（AI 驱动）。"""
    pass


class StopDiscussionRequest(BaseModel):
    """手动结束讨论。"""
    conclusion: str | None = Field(default=None, description="自定义结论（可选）")


# ============================================================
# 实体模型 (Domain Models)
# ============================================================


class PanelistOut(BaseModel):
    """嘉宾输出模型。"""
    id: int
    discussion_id: str
    name: str
    title: str
    stance: str
    color: str
    role: str  # "host" | "expert"
    status: str  # "idle" | "preparing" | "speaking"
    focus: str | None = None


class SpeechOut(BaseModel):
    """发言输出模型。"""
    id: int
    discussion_id: str
    panelist_id: int
    panelist_name: str
    panelist_title: str
    panelist_color: str
    panelist_role: str
    content: str
    speech_type: str  # "open" | "comment" | "rebut" | "question" | "summary"
    round_num: int
    created_at: float


class FindingOut(BaseModel):
    """共识/分歧输出模型。"""
    id: int
    discussion_id: str
    type: str  # "consensus" | "disagreement"
    content: str
    round_num: int


class DiscussionOut(BaseModel):
    """讨论输出模型。"""
    id: str
    topic: str
    status: str
    expert_count: int
    created_at: float
    concluded_at: float | None = None
    conclusion: str | None = None


class DiscussionDetailOut(DiscussionOut):
    """讨论详情（含关联数据）。"""
    panelists: list[PanelistOut] = []
    speeches: list[SpeechOut] = []
    findings: list[FindingOut] = []


class PanelistGenerateOut(BaseModel):
    """AI 生成的嘉宾阵容输出。"""
    panelists: list[PanelistOut]


class DiscussionListOut(BaseModel):
    """讨论列表输出。"""
    discussions: list[DiscussionOut]
    count: int


class SSEEvent(BaseModel):
    """SSE 事件模型。"""
    event: str  # "panelist_update" | "speech" | "finding" | "status" | "concluded"
    data: dict

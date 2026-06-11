"""业务逻辑层 — 讨论生命周期管理、嘉宾生成、发言调度。

核心职责：
1. 讨论状态机：configuring → active → concluded
2. 嘉宾生成流程：调用 LLM → 解析 → 存储
3. 讨论驱动引擎：轮次管理、发言调度、收敛追踪
4. 共识/分歧实时提取
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from panel_studio.db import PanelDB
from panel_studio.llm import (
    decide_next_speaker,
    extract_findings,
    generate_panelists,
    generate_speech,
)
from panel_studio.schema import PANEL_COLORS

logger = logging.getLogger(__name__)

# 每轮最大发言数（防止无限循环）
MAX_SPEECHES_PER_ROUND = 12
# 总最大轮次
MAX_ROUNDS = 5


class PanelCore:
    """圆桌讨论核心业务逻辑。

    Args:
        db: PanelDB 实例
        sse: SSE 管理器（可选，用于实时推送）
    """

    def __init__(self, db: PanelDB, sse=None):
        self.db = db
        self.sse = sse
        self._running: dict[str, bool] = {}  # discussion_id → 是否正在运行

    # ================================================================
    # 讨论 CRUD
    # ================================================================

    def create_discussion(self, topic: str, expert_count: int = 4) -> dict[str, Any]:
        """创建新讨论（configuring 状态）。"""
        conn = self.db.connect()
        try:
            disc = self.db.create_discussion(conn, topic=topic, expert_count=expert_count)
            return {"ok": True, "discussion": disc}
        finally:
            conn.close()

    def get_discussion(self, discussion_id: str) -> dict[str, Any] | None:
        """获取讨论详情（含关联数据）。"""
        conn = self.db.connect()
        try:
            disc = self.db.get_discussion(conn, discussion_id)
            if not disc:
                return None

            panelists = self.db.get_panelists(conn, discussion_id)
            speeches = self.db.get_speeches(conn, discussion_id)
            findings = self.db.get_findings(conn, discussion_id)

            return {
                "ok": True,
                "discussion": disc,
                "panelists": panelists,
                "speeches": speeches,
                "findings": findings,
            }
        finally:
            conn.close()

    def list_discussions(self, *, status: str | None = None) -> dict[str, Any]:
        """列出讨论。"""
        conn = self.db.connect()
        try:
            discussions = self.db.list_discussions(conn, status=status)
            return {"ok": True, "discussions": discussions, "count": len(discussions)}
        finally:
            conn.close()

    # ================================================================
    # 嘉宾生成
    # ================================================================

    async def generate_panelists_for_discussion(self, discussion_id: str) -> dict[str, Any]:
        """为讨论生成嘉宾阵容（AI 调用）。"""
        conn = self.db.connect()
        try:
            disc = self.db.get_discussion(conn, discussion_id)
            if not disc:
                return {"ok": False, "error": "讨论不存在"}
            if disc["status"] != "configuring":
                return {"ok": False, "error": "讨论已启动，无法重新生成嘉宾"}

            topic = disc["topic"]
            expert_count = disc["expert_count"]

            # 调用 LLM 生成嘉宾
            result = await generate_panelists(topic, expert_count)

            # 清除旧嘉宾
            self.db.clear_panelists(conn, discussion_id)

            # 添加主持人
            host_data = result["host"]
            host = self.db.add_panelist(
                conn,
                discussion_id=discussion_id,
                name=host_data["name"],
                title=host_data["title"],
                stance=host_data.get("stance", "中立引导"),
                color=PANEL_COLORS[0],
                role="host",
            )

            # 添加专家
            experts = []
            for i, exp_data in enumerate(result["experts"]):
                color = PANEL_COLORS[(i + 1) % len(PANEL_COLORS)]
                expert = self.db.add_panelist(
                    conn,
                    discussion_id=discussion_id,
                    name=exp_data["name"],
                    title=exp_data["title"],
                    stance=exp_data.get("stance", ""),
                    color=color,
                    role="expert",
                )
                experts.append(expert)

            # 推送 SSE 事件
            if self.sse:
                await self.sse.publish(discussion_id, "panelists_generated", {
                    "panelists": [host] + experts,
                })

            return {"ok": True, "panelists": [host] + experts}
        finally:
            conn.close()

    # ================================================================
    # 讨论控制
    # ================================================================

    async def confirm_and_start(self, discussion_id: str) -> dict[str, Any]:
        """确认嘉宾阵容并启动讨论。"""
        conn = self.db.connect()
        try:
            disc = self.db.get_discussion(conn, discussion_id)
            if not disc:
                return {"ok": False, "error": "讨论不存在"}
            if disc["status"] != "configuring":
                return {"ok": False, "error": "讨论已启动"}

            panelists = self.db.get_panelists(conn, discussion_id)
            if len(panelists) < 2:
                return {"ok": False, "error": "至少需要2位嘉宾"}

            # 更新状态为 active
            disc = self.db.update_discussion_status(conn, discussion_id, "active")

            # 推送状态变更
            if self.sse:
                await self.sse.publish(discussion_id, "status_changed", {
                    "status": "active",
                })

            return {"ok": True, "discussion": disc, "panelists": panelists}
        finally:
            conn.close()

    async def stop_discussion(self, discussion_id: str, conclusion: str | None = None) -> dict[str, Any]:
        """手动结束讨论。"""
        conn = self.db.connect()
        try:
            disc = self.db.get_discussion(conn, discussion_id)
            if not disc:
                return {"ok": False, "error": "讨论不存在"}
            if disc["status"] == "concluded":
                return {"ok": False, "error": "讨论已结束"}

            # 停止运行中的讨论引擎
            self._running[discussion_id] = False

            # 如果没有提供结论，生成一个
            if not conclusion:
                conclusion = "讨论已手动结束。"

            disc = self.db.update_discussion_status(
                conn, discussion_id, "concluded", conclusion=conclusion,
            )

            if self.sse:
                await self.sse.publish(discussion_id, "concluded", {
                    "conclusion": conclusion,
                })

            return {"ok": True, "discussion": disc}
        finally:
            conn.close()

    # ================================================================
    # 讨论引擎（核心！）
    # ================================================================

    async def run_discussion(self, discussion_id: str) -> dict[str, Any]:
        """运行讨论引擎 — 自动驱动整个讨论流程。

        流程：
        1. 主持人开场
        2. 循环：专家发言 → 提取共识/分歧 → 判断是否继续
        3. 主持人总结
        4. 结束讨论
        """
        self._running[discussion_id] = True

        conn = self.db.connect()
        try:
            disc = self.db.get_discussion(conn, discussion_id)
            if not disc or disc["status"] != "active":
                return {"ok": False, "error": "讨论不存在或未激活"}

            panelists = self.db.get_panelists(conn, discussion_id)
            host = next((p for p in panelists if p["role"] == "host"), None)
            experts = [p for p in panelists if p["role"] == "expert"]

            if not host:
                return {"ok": False, "error": "缺少主持人"}

            topic = disc["topic"]
        finally:
            conn.close()

        try:
            # === 第1步：主持人开场 ===
            await self._emit_speech(
                discussion_id, host, topic,
                speech_type="open", round_num=0,
            )

            # === 第2步：多轮讨论 ===
            for round_num in range(1, MAX_ROUNDS + 1):
                if not self._running.get(discussion_id):
                    break

                # 每轮内多位专家发言
                speeches_this_round = 0
                max_per_round = min(len(experts) * 2, MAX_SPEECHES_PER_ROUND)

                for _ in range(max_per_round):
                    if not self._running.get(discussion_id):
                        break

                    # 决定下一位发言者
                    transcript = self._build_transcript(discussion_id)
                    last_speaker = self._get_last_speaker(discussion_id)

                    candidates = [
                        p for p in panelists
                        if p["name"] != last_speaker
                    ]

                    next_name = await decide_next_speaker(
                        topic, transcript, candidates, last_speaker,
                    )

                    speaker = next(
                        (p for p in panelists if p["name"] == next_name),
                        experts[0],
                    )

                    # 生成发言
                    await self._emit_speech(
                        discussion_id, speaker, topic,
                        speech_type="comment", round_num=round_num,
                    )
                    speeches_this_round += 1

                    # 每3次发言提取一次共识/分歧
                    if speeches_this_round % 3 == 0:
                        await self._extract_and_publish_findings(discussion_id, topic, round_num)

                # 轮次结束，提取共识/分歧
                await self._extract_and_publish_findings(discussion_id, topic, round_num)

                # 检查是否还有话要说（简化：超过2轮且发言充分就结束）
                if round_num >= 2 and speeches_this_round >= len(experts):
                    break

            # === 第3步：主持人总结 ===
            if self._running.get(discussion_id):
                await self._emit_speech(
                    discussion_id, host, topic,
                    speech_type="summary", round_num=MAX_ROUNDS + 1,
                )

            # === 第4步：结束讨论 ===
            if self._running.get(discussion_id):
                conclusion = self._build_transcript(discussion_id)
                # 提取最后的结论作为 discussion conclusion
                conn = self.db.connect()
                try:
                    # 用 LLM 生成简短结论
                    from panel_studio.llm import _call_llm
                    summary_prompt = f"请用2-3句话总结以下讨论的核心结论：\n\n{conclusion}"
                    short_conclusion = await _call_llm(
                        [{"role": "user", "content": summary_prompt}],
                        temperature=0.3, max_tokens=200,
                    )
                except Exception:
                    short_conclusion = "讨论已结束。"
                finally:
                    conn.close()

                await self.stop_discussion(discussion_id, conclusion=short_conclusion)

            return {"ok": True, "discussion_id": discussion_id}

        except Exception as e:
            logger.exception("讨论引擎异常: %s", e)
            self._running[discussion_id] = False
            if self.sse:
                await self.sse.publish(discussion_id, "error", {"error": str(e)})
            return {"ok": False, "error": str(e)}

    async def _emit_speech(
        self,
        discussion_id: str,
        panelist: dict[str, str],
        topic: str,
        *,
        speech_type: str = "comment",
        round_num: int = 0,
    ) -> dict[str, Any]:
        """生成并推送一次发言。"""
        # 更新嘉宾状态为"准备发言"
        conn = self.db.connect()
        try:
            self.db.update_panelist_status(conn, panelist["id"], "preparing")
        finally:
            conn.close()

        if self.sse:
            await self.sse.publish(discussion_id, "panelist_update", {
                "panelist_id": panelist["id"],
                "status": "preparing",
            })

        # 构建 transcript
        transcript = self._build_transcript(discussion_id)

        # 生成发言内容
        content = await generate_speech(
            role=panelist["role"],
            panelist=panelist,
            topic=topic,
            transcript=transcript,
            speech_type=speech_type,
        )

        # 更新嘉宾状态为"发言中"
        conn = self.db.connect()
        try:
            self.db.update_panelist_status(conn, panelist["id"], "speaking")

            # 保存发言
            speech = self.db.add_speech(
                conn,
                discussion_id=discussion_id,
                panelist_id=panelist["id"],
                content=content,
                speech_type=speech_type,
                round_num=round_num,
            )
        finally:
            conn.close()

        # 推送发言事件
        if self.sse:
            await self.sse.publish(discussion_id, "speech", speech)

        # 更新嘉宾状态为"待机"
        conn = self.db.connect()
        try:
            self.db.update_panelist_status(conn, panelist["id"], "idle")
        finally:
            conn.close()

        if self.sse:
            await self.sse.publish(discussion_id, "panelist_update", {
                "panelist_id": panelist["id"],
                "status": "idle",
            })

        # 模拟发言间隔
        await asyncio.sleep(1.5)

        return speech

    async def _extract_and_publish_findings(
        self, discussion_id: str, topic: str, round_num: int,
    ) -> None:
        """提取并推送共识/分歧。"""
        transcript = self._build_transcript(discussion_id)
        if not transcript.strip():
            return

        try:
            findings_result = await extract_findings(topic, transcript)

            conn = self.db.connect()
            try:
                for content in findings_result.get("consensus", []):
                    finding = self.db.add_finding(
                        conn,
                        discussion_id=discussion_id,
                        finding_type="consensus",
                        content=content,
                        round_num=round_num,
                    )
                    if self.sse:
                        await self.sse.publish(discussion_id, "finding", finding)

                for content in findings_result.get("disagreement", []):
                    finding = self.db.add_finding(
                        conn,
                        discussion_id=discussion_id,
                        finding_type="disagreement",
                        content=content,
                        round_num=round_num,
                    )
                    if self.sse:
                        await self.sse.publish(discussion_id, "finding", finding)
            finally:
                conn.close()

        except Exception as e:
            logger.warning("提取共识/分歧失败: %s", e)

    def _build_transcript(self, discussion_id: str) -> str:
        """构建讨论记录文本。"""
        conn = self.db.connect()
        try:
            speeches = self.db.get_speeches(conn, discussion_id)
            if not speeches:
                return ""

            lines = []
            for s in speeches:
                role_label = "【主持人】" if s["panelist_role"] == "host" else ""
                lines.append(f"{role_label}{s['panelist_name']}（{s['panelist_title']}）：{s['content']}")
            return "\n".join(lines)
        finally:
            conn.close()

    def _get_last_speaker(self, discussion_id: str) -> str | None:
        """获取最后一位发言者姓名。"""
        conn = self.db.connect()
        try:
            speeches = self.db.get_speeches(conn, discussion_id)
            return speeches[-1]["panelist_name"] if speeches else None
        finally:
            conn.close()

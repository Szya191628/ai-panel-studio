"""SSE 事件管理 — 基于 asyncio.Queue 的事件分发。

简化 agent-roundtable 的 3 层架构为 2 层：
Python (core) → SSE (FastAPI StreamingResponse) → Client (EventSource)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SSEManager:
    """管理多个讨论的 SSE 连接。

    每个讨论有独立的事件队列集合，支持多客户端订阅同一讨论。
    """

    def __init__(self) -> None:
        # discussion_id → set of asyncio.Queue
        self._subscribers: dict[str, set[asyncio.Queue]] = {}

    def subscribe(self, discussion_id: str) -> asyncio.Queue:
        """订阅讨论事件，返回事件队列。"""
        if discussion_id not in self._subscribers:
            self._subscribers[discussion_id] = set()

        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[discussion_id].add(queue)
        logger.info("SSE 订阅: %s (当前 %d 个订阅者)", discussion_id, len(self._subscribers[discussion_id]))
        return queue

    def unsubscribe(self, discussion_id: str, queue: asyncio.Queue) -> None:
        """取消订阅。"""
        if discussion_id in self._subscribers:
            self._subscribers[discussion_id].discard(queue)
            if not self._subscribers[discussion_id]:
                del self._subscribers[discussion_id]
            logger.info("SSE 取消订阅: %s", discussion_id)

    async def publish(self, discussion_id: str, event: str, data: dict[str, Any]) -> None:
        """发布事件到讨论的所有订阅者。"""
        if discussion_id not in self._subscribers:
            return

        message = {
            "event": event,
            "data": data,
            "timestamp": time.time(),
        }

        dead_queues = []
        for queue in self._subscribers.get(discussion_id, set()):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead_queues.append(queue)

        # 清理死队列
        for q in dead_queues:
            self._subscribers[discussion_id].discard(q)

    async def stream(self, discussion_id: str, queue: asyncio.Queue):
        """生成 SSE 事件流（用于 FastAPI StreamingResponse）。"""
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield format_sse(message["event"], message["data"])
                except asyncio.TimeoutError:
                    # 发送心跳
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            self.unsubscribe(discussion_id, queue)


def format_sse(event: str, data: dict[str, Any]) -> str:
    """格式化 SSE 消息。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

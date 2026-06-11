"""数据库访问层 — SQLite CRUD 操作。

所有方法返回 dict（JSON-serializable），遵循 agent-roundtable 的 db.py 模式。
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from panel_studio.config import DB_PATH
from panel_studio.schema import (
    PANEL_COLORS,
    VALID_DISCUSSION_STATUSES,
    VALID_FINDING_TYPES,
    VALID_PANELIST_ROLES,
    VALID_PANELIST_STATUSES,
    VALID_SPEECH_TYPES,
    init_db,
)


class PanelDB:
    """SQLite 存储层。

    Args:
        db_path: 数据库文件路径，默认从 config.DB_PATH 读取。
    """

    def __init__(self, db_path: Path | str | None = None):
        self._path = Path(db_path) if db_path else DB_PATH

    @property
    def db_path(self) -> Path:
        return self._path

    def connect(self) -> sqlite3.Connection:
        """打开数据库连接（WAL 模式 + 外键约束）。"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        init_db(conn)
        return conn

    # ================================================================
    # Discussion CRUD
    # ================================================================

    def create_discussion(
        self,
        conn: sqlite3.Connection,
        *,
        topic: str,
        expert_count: int = 4,
        discussion_id: str | None = None,
    ) -> dict[str, Any]:
        """创建新讨论。"""
        if not topic or not topic.strip():
            raise ValueError("topic 不能为空")
        if expert_count < 2 or expert_count > 8:
            raise ValueError("expert_count 必须在 2-8 之间")

        import secrets
        did = discussion_id or secrets.token_urlsafe(12)
        now = time.time()

        conn.execute(
            """INSERT INTO discussions (id, topic, status, expert_count, created_at)
               VALUES (?, ?, 'configuring', ?, ?)""",
            (did, topic.strip(), expert_count, now),
        )
        conn.commit()
        return self.get_discussion(conn, did)

    def get_discussion(self, conn: sqlite3.Connection, discussion_id: str) -> dict[str, Any] | None:
        """获取单个讨论。"""
        row = conn.execute(
            "SELECT * FROM discussions WHERE id = ?", (discussion_id,)
        ).fetchone()
        if not row:
            return None
        return dict(row)

    def list_discussions(
        self,
        conn: sqlite3.Connection,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """列出讨论。"""
        if status:
            if status not in VALID_DISCUSSION_STATUSES:
                raise ValueError(f"无效状态: {status}")
            rows = conn.execute(
                "SELECT * FROM discussions WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM discussions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def update_discussion_status(
        self,
        conn: sqlite3.Connection,
        discussion_id: str,
        status: str,
        *,
        conclusion: str | None = None,
    ) -> dict[str, Any] | None:
        """更新讨论状态。"""
        if status not in VALID_DISCUSSION_STATUSES:
            raise ValueError(f"无效状态: {status}")

        now = time.time()
        if status == "concluded":
            conn.execute(
                "UPDATE discussions SET status = ?, concluded_at = ?, conclusion = ? WHERE id = ?",
                (status, now, conclusion, discussion_id),
            )
        else:
            conn.execute(
                "UPDATE discussions SET status = ? WHERE id = ?",
                (status, discussion_id),
            )
        conn.commit()
        return self.get_discussion(conn, discussion_id)

    # ================================================================
    # Panelist CRUD
    # ================================================================

    def add_panelist(
        self,
        conn: sqlite3.Connection,
        *,
        discussion_id: str,
        name: str,
        title: str,
        stance: str,
        color: str,
        role: str = "expert",
    ) -> dict[str, Any]:
        """添加嘉宾。"""
        if role not in VALID_PANELIST_ROLES:
            raise ValueError(f"无效角色: {role}")

        cur = conn.execute(
            """INSERT INTO panelists (discussion_id, name, title, stance, color, role, status)
               VALUES (?, ?, ?, ?, ?, ?, 'idle')""",
            (discussion_id, name, title, stance, color, role),
        )
        conn.commit()
        return self.get_panelist(conn, cur.lastrowid)

    def get_panelist(self, conn: sqlite3.Connection, panelist_id: int) -> dict[str, Any] | None:
        """获取单个嘉宾。"""
        row = conn.execute(
            "SELECT * FROM panelists WHERE id = ?", (panelist_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_panelists(self, conn: sqlite3.Connection, discussion_id: str) -> list[dict[str, Any]]:
        """获取讨论的所有嘉宾（按 role 排序：host 在前）。"""
        rows = conn.execute(
            """SELECT * FROM panelists WHERE discussion_id = ?
               ORDER BY CASE role WHEN 'host' THEN 0 ELSE 1 END, id""",
            (discussion_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_panelist_status(
        self,
        conn: sqlite3.Connection,
        panelist_id: int,
        status: str,
        *,
        focus: str | None = None,
    ) -> dict[str, Any] | None:
        """更新嘉宾状态。"""
        if status not in VALID_PANELIST_STATUSES:
            raise ValueError(f"无效状态: {status}")

        if focus is not None:
            conn.execute(
                "UPDATE panelists SET status = ?, focus = ? WHERE id = ?",
                (status, focus, panelist_id),
            )
        else:
            conn.execute(
                "UPDATE panelists SET status = ? WHERE id = ?",
                (status, panelist_id),
            )
        conn.commit()
        return self.get_panelist(conn, panelist_id)

    def clear_panelists(self, conn: sqlite3.Connection, discussion_id: str) -> None:
        """清除讨论的所有嘉宾（用于重新生成）。"""
        conn.execute("DELETE FROM panelists WHERE discussion_id = ?", (discussion_id,))
        conn.commit()

    # ================================================================
    # Speech CRUD
    # ================================================================

    def add_speech(
        self,
        conn: sqlite3.Connection,
        *,
        discussion_id: str,
        panelist_id: int,
        content: str,
        speech_type: str = "comment",
        round_num: int = 0,
    ) -> dict[str, Any]:
        """添加发言。"""
        if speech_type not in VALID_SPEECH_TYPES:
            raise ValueError(f"无效发言类型: {speech_type}")
        if not content or not content.strip():
            raise ValueError("content 不能为空")

        now = time.time()
        cur = conn.execute(
            """INSERT INTO speeches (discussion_id, panelist_id, content, speech_type, round_num, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (discussion_id, panelist_id, content.strip(), speech_type, round_num, now),
        )
        conn.commit()
        return self.get_speech(conn, cur.lastrowid)

    def get_speech(self, conn: sqlite3.Connection, speech_id: int) -> dict[str, Any] | None:
        """获取单条发言（含嘉宾信息）。"""
        row = conn.execute(
            """SELECT s.*, p.name AS panelist_name, p.title AS panelist_title,
                      p.color AS panelist_color, p.role AS panelist_role
               FROM speeches s JOIN panelists p ON s.panelist_id = p.id
               WHERE s.id = ?""",
            (speech_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_speeches(
        self,
        conn: sqlite3.Connection,
        discussion_id: str,
        *,
        since_round: int | None = None,
    ) -> list[dict[str, Any]]:
        """获取讨论的发言列表（含嘉宾信息）。"""
        if since_round is not None:
            rows = conn.execute(
                """SELECT s.*, p.name AS panelist_name, p.title AS panelist_title,
                          p.color AS panelist_color, p.role AS panelist_role
                   FROM speeches s JOIN panelists p ON s.panelist_id = p.id
                   WHERE s.discussion_id = ? AND s.round_num >= ?
                   ORDER BY s.id""",
                (discussion_id, since_round),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT s.*, p.name AS panelist_name, p.title AS panelist_title,
                          p.color AS panelist_color, p.role AS panelist_role
                   FROM speeches s JOIN panelists p ON s.panelist_id = p.id
                   WHERE s.discussion_id = ?
                   ORDER BY s.id""",
                (discussion_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_speech_count(self, conn: sqlite3.Connection, discussion_id: str) -> int:
        """获取发言总数。"""
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM speeches WHERE discussion_id = ?",
            (discussion_id,),
        ).fetchone()
        return row["cnt"] if row else 0

    def get_current_round(self, conn: sqlite3.Connection, discussion_id: str) -> int:
        """获取当前轮次。"""
        row = conn.execute(
            "SELECT MAX(round_num) AS max_round FROM speeches WHERE discussion_id = ?",
            (discussion_id,),
        ).fetchone()
        return row["max_round"] if row and row["max_round"] else 0

    # ================================================================
    # Finding CRUD
    # ================================================================

    def add_finding(
        self,
        conn: sqlite3.Connection,
        *,
        discussion_id: str,
        finding_type: str,
        content: str,
        round_num: int = 0,
    ) -> dict[str, Any]:
        """添加共识/分歧。"""
        if finding_type not in VALID_FINDING_TYPES:
            raise ValueError(f"无效发现类型: {finding_type}")

        cur = conn.execute(
            """INSERT INTO findings (discussion_id, type, content, round_num)
               VALUES (?, ?, ?, ?)""",
            (discussion_id, finding_type, content, round_num),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM findings WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)

    def get_findings(
        self,
        conn: sqlite3.Connection,
        discussion_id: str,
        *,
        finding_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """获取共识/分歧列表。"""
        if finding_type:
            rows = conn.execute(
                "SELECT * FROM findings WHERE discussion_id = ? AND type = ? ORDER BY id",
                (discussion_id, finding_type),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM findings WHERE discussion_id = ? ORDER BY id",
                (discussion_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def clear_findings(self, conn: sqlite3.Connection, discussion_id: str) -> None:
        """清除讨论的所有发现（用于重新提取）。"""
        conn.execute("DELETE FROM findings WHERE discussion_id = ?", (discussion_id,))
        conn.commit()

"""SQLite Schema — DDL 定义与版本迁移。

SDD 阶段核心产物：数据模型的持久化层定义。
参考 agent-roundtable 的 schema 模式：
- 单一 SCHEMA_SQL 字符串
- CREATE TABLE IF NOT EXISTS 幂等执行
- PRAGMA user_version 版本迁移
- CHECK 约束 + Python 端双重验证
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

# ============================================================
# 验证常量 (与 CHECK 约束对齐)
# ============================================================

VALID_DISCUSSION_STATUSES = {"configuring", "active", "concluded"}
VALID_PANELIST_ROLES = {"host", "expert"}
VALID_PANELIST_STATUSES = {"idle", "preparing", "speaking"}
VALID_SPEECH_TYPES = {"open", "comment", "rebut", "question", "summary"}
VALID_FINDING_TYPES = {"consensus", "disagreement"}

# ============================================================
# 嘉宾色板 (8色)
# ============================================================

PANEL_COLORS = [
    "#3b82f6",  # 蓝
    "#ef4444",  # 红
    "#10b981",  # 绿
    "#f59e0b",  # 橙
    "#8b5cf6",  # 紫
    "#ec4899",  # 粉
    "#06b6d4",  # 青
    "#f97316",  # 深橙
]

# ============================================================
# Schema DDL
# ============================================================

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS discussions (
    id              TEXT PRIMARY KEY,
    topic           TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'configuring'
                    CHECK (status IN ('configuring', 'active', 'concluded')),
    expert_count    INTEGER NOT NULL DEFAULT 4 CHECK (expert_count BETWEEN 2 AND 8),
    created_at      REAL NOT NULL,
    concluded_at    REAL,
    conclusion      TEXT
);

CREATE TABLE IF NOT EXISTS panelists (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    discussion_id   TEXT NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    title           TEXT NOT NULL,
    stance          TEXT NOT NULL DEFAULT '',
    color           TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('host', 'expert')),
    status          TEXT NOT NULL DEFAULT 'idle' CHECK (status IN ('idle', 'preparing', 'speaking')),
    focus           TEXT,
    UNIQUE(discussion_id, name)
);

CREATE TABLE IF NOT EXISTS speeches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    discussion_id   TEXT NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
    panelist_id     INTEGER NOT NULL REFERENCES panelists(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    speech_type     TEXT NOT NULL DEFAULT 'comment'
                    CHECK (speech_type IN ('open', 'comment', 'rebut', 'question', 'summary')),
    round_num       INTEGER NOT NULL DEFAULT 0,
    created_at      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    discussion_id   TEXT NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
    type            TEXT NOT NULL CHECK (type IN ('consensus', 'disagreement')),
    content         TEXT NOT NULL,
    round_num       INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_panelists_discussion ON panelists(discussion_id);
CREATE INDEX IF NOT EXISTS idx_speeches_discussion ON speeches(discussion_id);
CREATE INDEX IF NOT EXISTS idx_speeches_round ON speeches(discussion_id, round_num);
CREATE INDEX IF NOT EXISTS idx_findings_discussion ON findings(discussion_id);
"""

# ============================================================
# 迁移系统
# ============================================================

_MIGRATIONS: list[Callable[[sqlite3.Connection], None]] = [
    # _migrate_v0_to_v1,  # 未来扩展
]


def migrate_db(conn: sqlite3.Connection) -> None:
    """根据 PRAGMA user_version 执行增量迁移。"""
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for target_ver, migration_fn in enumerate(_MIGRATIONS, start=1):
        if target_ver > current:
            migration_fn(conn)
            conn.execute(f"PRAGMA user_version = {target_ver}")


def init_db(conn: sqlite3.Connection) -> None:
    """初始化数据库：执行 DDL + 迁移。"""
    conn.executescript(SCHEMA_SQL)
    migrate_db(conn)

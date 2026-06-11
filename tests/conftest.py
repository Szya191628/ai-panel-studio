"""测试 Fixtures — 内存 SQLite + 通用工具。"""

from __future__ import annotations

import sqlite3

import pytest

from panel_studio.db import PanelDB
from panel_studio.schema import init_db


@pytest.fixture
def db(tmp_path):
    """创建临时数据库实例。"""
    db_path = tmp_path / "test_panel.db"
    return PanelDB(db_path=db_path)


@pytest.fixture
def conn(db):
    """创建数据库连接（测试结束自动关闭）。"""
    connection = db.connect()
    yield connection
    connection.close()


@pytest.fixture
def sample_discussion(db, conn):
    """创建一个样例讨论。"""
    return db.create_discussion(conn, topic="AI是否会取代程序员？", expert_count=4)


@pytest.fixture
def sample_panelists(db, conn, sample_discussion):
    """为样例讨论创建嘉宾。"""
    did = sample_discussion["id"]
    host = db.add_panelist(
        conn, discussion_id=did, name="张主持", title="资深科技主持人",
        stance="中立引导", color="#3b82f6", role="host",
    )
    experts = []
    for i, (name, title, stance, color) in enumerate([
        ("李博士", "AI研究员", "AI将增强而非取代程序员", "#ef4444"),
        ("王架构师", "资深后端架构师", "AI会取代大部分重复编码工作", "#10b981"),
        ("赵教授", "计算机科学教授", "编程本质是思维训练，AI无法替代", "#f59e0b"),
        ("陈CTO", "创业公司CTO", "AI将重塑整个软件工程范式", "#8b5cf6"),
    ]):
        expert = db.add_panelist(
            conn, discussion_id=did, name=name, title=title,
            stance=stance, color=color, role="expert",
        )
        experts.append(expert)
    return [host] + experts

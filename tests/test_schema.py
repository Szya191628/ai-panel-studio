"""Schema 测试 — 表创建、约束、迁移。"""

from __future__ import annotations

import sqlite3

from panel_studio.schema import SCHEMA_SQL, init_db, migrate_db


class TestSchemaCreation:
    """测试表创建的幂等性和结构。"""

    def test_schema_creates_tables(self, tmp_path):
        """DDL 应创建所有表。"""
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        init_db(conn)

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        assert "discussions" in tables
        assert "panelists" in tables
        assert "speeches" in tables
        assert "findings" in tables
        conn.close()

    def test_schema_idempotent(self, tmp_path):
        """重复执行 DDL 不应报错。"""
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        init_db(conn)
        init_db(conn)  # 第二次执行
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        assert len(tables) >= 4
        conn.close()

    def test_indexes_created(self, tmp_path):
        """应创建性能索引。"""
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        init_db(conn)

        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            ).fetchall()
        }
        assert "idx_panelists_discussion" in indexes
        assert "idx_speeches_discussion" in indexes
        assert "idx_findings_discussion" in indexes
        conn.close()


class TestSchemaConstraints:
    """测试 CHECK 约束。"""

    def test_discussion_status_constraint(self, conn):
        """讨论状态必须是有效值。"""
        try:
            conn.execute(
                "INSERT INTO discussions (id, topic, status, expert_count, created_at) VALUES (?, ?, ?, ?, ?)",
                ("t1", "test", "invalid_status", 4, 100.0),
            )
            assert False, "应该抛出 IntegrityError"
        except sqlite3.IntegrityError:
            pass

    def test_panelist_role_constraint(self, conn):
        """嘉宾角色必须是 host 或 expert。"""
        conn.execute(
            "INSERT INTO discussions (id, topic, status, expert_count, created_at) VALUES (?, ?, ?, ?, ?)",
            ("t1", "test", "configuring", 4, 100.0),
        )
        try:
            conn.execute(
                "INSERT INTO panelists (discussion_id, name, title, color, role, status) VALUES (?, ?, ?, ?, ?, ?)",
                ("t1", "test", "test", "#fff", "invalid_role", "idle"),
            )
            assert False, "应该抛出 IntegrityError"
        except sqlite3.IntegrityError:
            pass

    def test_expert_count_range(self, conn):
        """专家人数必须在 2-8 之间。"""
        try:
            conn.execute(
                "INSERT INTO discussions (id, topic, status, expert_count, created_at) VALUES (?, ?, ?, ?, ?)",
                ("t1", "test", "configuring", 1, 100.0),  # < 2
            )
            assert False, "应该抛出 IntegrityError"
        except sqlite3.IntegrityError:
            pass

    def test_migration_preserves_version(self, tmp_path):
        """迁移后版本号应正确更新。"""
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        init_db(conn)
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        # 当前没有迁移，版本应为 0
        assert version == 0
        conn.close()

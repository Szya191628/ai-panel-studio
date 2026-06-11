"""数据库层测试 — CRUD 操作、边界条件。"""

from __future__ import annotations

import pytest

from panel_studio.db import PanelDB


class TestDiscussionCRUD:
    """讨论 CRUD 操作。"""

    def test_create_discussion(self, db, conn):
        """创建讨论应返回完整记录。"""
        disc = db.create_discussion(conn, topic="测试话题", expert_count=3)
        assert disc["id"] is not None
        assert disc["topic"] == "测试话题"
        assert disc["status"] == "configuring"
        assert disc["expert_count"] == 3
        assert disc["created_at"] > 0

    def test_create_discussion_strips_whitespace(self, db, conn):
        """话题前后空格应被去除。"""
        disc = db.create_discussion(conn, topic="  测试话题  ")
        assert disc["topic"] == "测试话题"

    def test_create_discussion_empty_topic_raises(self, db, conn):
        """空话题应抛出 ValueError。"""
        with pytest.raises(ValueError, match="topic"):
            db.create_discussion(conn, topic="")
        with pytest.raises(ValueError, match="topic"):
            db.create_discussion(conn, topic="   ")

    def test_create_discussion_invalid_expert_count(self, db, conn):
        """无效专家人数应抛出 ValueError。"""
        with pytest.raises(ValueError, match="expert_count"):
            db.create_discussion(conn, topic="test", expert_count=1)
        with pytest.raises(ValueError, match="expert_count"):
            db.create_discussion(conn, topic="test", expert_count=9)

    def test_get_discussion(self, db, conn, sample_discussion):
        """获取讨论应返回正确记录。"""
        disc = db.get_discussion(conn, sample_discussion["id"])
        assert disc is not None
        assert disc["topic"] == sample_discussion["topic"]

    def test_get_discussion_not_found(self, db, conn):
        """不存在的讨论应返回 None。"""
        assert db.get_discussion(conn, "nonexistent") is None

    def test_list_discussions(self, db, conn):
        """列出讨论应按创建时间倒序。"""
        import time
        d1 = db.create_discussion(conn, topic="话题1")
        time.sleep(0.01)
        d2 = db.create_discussion(conn, topic="话题2")
        time.sleep(0.01)
        d3 = db.create_discussion(conn, topic="话题3")
        discussions = db.list_discussions(conn)
        assert len(discussions) == 3
        # 按 created_at DESC 排序，最新在前
        assert discussions[0]["id"] == d3["id"]
        assert discussions[1]["id"] == d2["id"]
        assert discussions[2]["id"] == d1["id"]

    def test_list_discussions_filter_status(self, db, conn):
        """按状态过滤讨论。"""
        d1 = db.create_discussion(conn, topic="话题1")
        db.create_discussion(conn, topic="话题2")
        db.update_discussion_status(conn, d1["id"], "active")

        active = db.list_discussions(conn, status="active")
        configuring = db.list_discussions(conn, status="configuring")
        assert len(active) == 1
        assert len(configuring) == 1

    def test_update_discussion_status_to_concluded(self, db, conn, sample_discussion):
        """结束讨论应设置 concluded_at 和 conclusion。"""
        disc = db.update_discussion_status(
            conn, sample_discussion["id"], "concluded", conclusion="测试结论"
        )
        assert disc["status"] == "concluded"
        assert disc["concluded_at"] is not None
        assert disc["conclusion"] == "测试结论"


class TestPanelistCRUD:
    """嘉宾 CRUD 操作。"""

    def test_add_panelist(self, db, conn, sample_discussion):
        """添加嘉宾应返回完整记录。"""
        p = db.add_panelist(
            conn,
            discussion_id=sample_discussion["id"],
            name="张三", title="AI研究员", stance="支持AI", color="#3b82f6", role="expert",
        )
        assert p["name"] == "张三"
        assert p["role"] == "expert"
        assert p["status"] == "idle"

    def test_add_panelist_invalid_role(self, db, conn, sample_discussion):
        """无效角色应抛出 ValueError。"""
        with pytest.raises(ValueError, match="角色"):
            db.add_panelist(
                conn,
                discussion_id=sample_discussion["id"],
                name="张三", title="AI研究员", stance="", color="#fff", role="invalid",
            )

    def test_get_panelists_ordered_by_role(self, db, conn, sample_panelists):
        """嘉宾列表应按角色排序（host 在前）。"""
        did = sample_panelists[0]["discussion_id"]
        panelists = db.get_panelists(conn, did)
        assert panelists[0]["role"] == "host"
        for p in panelists[1:]:
            assert p["role"] == "expert"

    def test_update_panelist_status(self, db, conn, sample_panelists):
        """更新嘉宾状态。"""
        p = sample_panelists[1]
        updated = db.update_panelist_status(conn, p["id"], "speaking", focus="正在分析AI影响")
        assert updated["status"] == "speaking"
        assert updated["focus"] == "正在分析AI影响"

    def test_clear_panelists(self, db, conn, sample_discussion, sample_panelists):
        """清除嘉宾应删除所有记录。"""
        db.clear_panelists(conn, sample_discussion["id"])
        panelists = db.get_panelists(conn, sample_discussion["id"])
        assert len(panelists) == 0


class TestSpeechCRUD:
    """发言 CRUD 操作。"""

    def test_add_speech(self, db, conn, sample_discussion, sample_panelists):
        """添加发言应返回完整记录（含嘉宾信息）。"""
        p = sample_panelists[1]
        speech = db.add_speech(
            conn,
            discussion_id=sample_discussion["id"],
            panelist_id=p["id"],
            content="我认为AI将改变编程方式",
            speech_type="comment",
            round_num=1,
        )
        assert speech["content"] == "我认为AI将改变编程方式"
        assert speech["panelist_name"] == p["name"]
        assert speech["panelist_color"] == p["color"]

    def test_add_speech_empty_content_raises(self, db, conn, sample_discussion, sample_panelists):
        """空内容应抛出 ValueError。"""
        with pytest.raises(ValueError, match="content"):
            db.add_speech(
                conn,
                discussion_id=sample_discussion["id"],
                panelist_id=sample_panelists[0]["id"],
                content="",
            )

    def test_add_speech_invalid_type_raises(self, db, conn, sample_discussion, sample_panelists):
        """无效发言类型应抛出 ValueError。"""
        with pytest.raises(ValueError, match="发言类型"):
            db.add_speech(
                conn,
                discussion_id=sample_discussion["id"],
                panelist_id=sample_panelists[0]["id"],
                content="test",
                speech_type="invalid",
            )

    def test_get_speeches_ordered_by_id(self, db, conn, sample_discussion, sample_panelists):
        """发言列表应按 ID 排序。"""
        did = sample_discussion["id"]
        p1, p2 = sample_panelists[0], sample_panelists[1]
        db.add_speech(conn, discussion_id=did, panelist_id=p1["id"], content="发言1", round_num=1)
        db.add_speech(conn, discussion_id=did, panelist_id=p2["id"], content="发言2", round_num=1)
        db.add_speech(conn, discussion_id=did, panelist_id=p1["id"], content="发言3", round_num=2)

        speeches = db.get_speeches(conn, did)
        assert len(speeches) == 3
        assert speeches[0]["content"] == "发言1"
        assert speeches[2]["content"] == "发言3"

    def test_get_speeches_since_round(self, db, conn, sample_discussion, sample_panelists):
        """按轮次过滤发言。"""
        did = sample_discussion["id"]
        p = sample_panelists[0]
        db.add_speech(conn, discussion_id=did, panelist_id=p["id"], content="第1轮", round_num=1)
        db.add_speech(conn, discussion_id=did, panelist_id=p["id"], content="第2轮", round_num=2)
        db.add_speech(conn, discussion_id=did, panelist_id=p["id"], content="第3轮", round_num=3)

        round2_plus = db.get_speeches(conn, did, since_round=2)
        assert len(round2_plus) == 2
        assert round2_plus[0]["content"] == "第2轮"

    def test_get_current_round(self, db, conn, sample_discussion, sample_panelists):
        """获取当前轮次。"""
        did = sample_discussion["id"]
        p = sample_panelists[0]
        assert db.get_current_round(conn, did) == 0  # 无发言

        db.add_speech(conn, discussion_id=did, panelist_id=p["id"], content="test", round_num=1)
        assert db.get_current_round(conn, did) == 1

        db.add_speech(conn, discussion_id=did, panelist_id=p["id"], content="test", round_num=3)
        assert db.get_current_round(conn, did) == 3


class TestFindingCRUD:
    """共识/分歧 CRUD 操作。"""

    def test_add_finding(self, db, conn, sample_discussion):
        """添加发现应返回完整记录。"""
        finding = db.add_finding(
            conn,
            discussion_id=sample_discussion["id"],
            finding_type="consensus",
            content="AI是工具而非替代品",
            round_num=1,
        )
        assert finding["type"] == "consensus"
        assert finding["content"] == "AI是工具而非替代品"

    def test_add_finding_invalid_type_raises(self, db, conn, sample_discussion):
        """无效发现类型应抛出 ValueError。"""
        with pytest.raises(ValueError, match="发现类型"):
            db.add_finding(
                conn,
                discussion_id=sample_discussion["id"],
                finding_type="invalid",
                content="test",
            )

    def test_get_findings_filter_type(self, db, conn, sample_discussion):
        """按类型过滤发现。"""
        did = sample_discussion["id"]
        db.add_finding(conn, discussion_id=did, finding_type="consensus", content="共识1", round_num=1)
        db.add_finding(conn, discussion_id=did, finding_type="disagreement", content="分歧1", round_num=1)
        db.add_finding(conn, discussion_id=did, finding_type="consensus", content="共识2", round_num=2)

        consensus = db.get_findings(conn, did, finding_type="consensus")
        disagreement = db.get_findings(conn, did, finding_type="disagreement")
        assert len(consensus) == 2
        assert len(disagreement) == 1

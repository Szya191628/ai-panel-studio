"""API 端点测试 — FastAPI TestClient。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """创建测试客户端（使用临时数据库）。"""
    # 重定向数据库路径
    monkeypatch.setattr("panel_studio.config.DB_PATH", tmp_path / "test.db")

    from panel_studio.app import app, db, core
    # 重新初始化 db 使用新路径
    from panel_studio.db import PanelDB
    new_db = PanelDB(db_path=tmp_path / "test.db")
    import panel_studio.app as app_module
    app_module.db = new_db
    app_module.core = type(core)(db=new_db, sse=app_module.sse)

    return TestClient(app)


class TestIndexPage:
    """首页测试。"""

    def test_index_returns_html(self, client):
        """首页应返回 HTML。"""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "AI Panel Studio" in resp.text


class TestDiscussionAPI:
    """讨论 API 测试。"""

    def test_create_discussion(self, client):
        """创建讨论。"""
        resp = client.post("/api/discussions", json={
            "topic": "AI的未来",
            "expert_count": 4,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["discussion"]["topic"] == "AI的未来"

    def test_create_discussion_empty_topic(self, client):
        """空话题应返回 400。"""
        resp = client.post("/api/discussions", json={
            "topic": "",
            "expert_count": 4,
        })
        assert resp.status_code == 400

    def test_create_discussion_invalid_expert_count(self, client):
        """无效专家人数应返回 400。"""
        resp = client.post("/api/discussions", json={
            "topic": "test",
            "expert_count": 1,
        })
        assert resp.status_code == 400

    def test_list_discussions(self, client):
        """列出讨论。"""
        client.post("/api/discussions", json={"topic": "话题1"})
        client.post("/api/discussions", json={"topic": "话题2"})

        resp = client.get("/api/discussions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2

    def test_get_discussion(self, client):
        """获取讨论详情。"""
        create_resp = client.post("/api/discussions", json={"topic": "测试"})
        did = create_resp.json()["discussion"]["id"]

        resp = client.get(f"/api/discussions/{did}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["discussion"]["topic"] == "测试"

    def test_get_discussion_not_found(self, client):
        """不存在的讨论应返回 404。"""
        resp = client.get("/api/discussions/nonexistent")
        assert resp.status_code == 404

    def test_studio_page(self, client):
        """演播厅页面应返回 HTML。"""
        create_resp = client.post("/api/discussions", json={"topic": "测试"})
        did = create_resp.json()["discussion"]["id"]

        resp = client.get(f"/studio/{did}")
        assert resp.status_code == 200
        assert "演播厅" in resp.text

"""LLM 调用层测试 — Mock 模式，不实际调用 API。"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from panel_studio.llm import (
    _extract_json,
    extract_findings,
    generate_panelists,
    generate_speech,
)


class TestExtractJson:
    """测试 JSON 提取逻辑。"""

    def test_extract_direct_json(self):
        """直接 JSON 字符串。"""
        result = _extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_extract_json_from_code_block(self):
        """从 markdown code block 提取。"""
        text = '''这是分析结果：
```json
{"host": {"name": "张三"}}
```
以上是结果。'''
        result = _extract_json(text)
        assert result == {"host": {"name": "张三"}}

    def test_extract_json_from_text(self):
        """从混合文本中提取。"""
        text = '根据分析，结果如下：{"consensus": ["观点1"]} 请参考。'
        result = _extract_json(text)
        assert result == {"consensus": ["观点1"]}

    def test_extract_json_array(self):
        """提取 JSON 数组。"""
        text = '结果：[{"name": "张三"}, {"name": "李四"}]'
        result = _extract_json(text)
        assert len(result) == 2

    def test_extract_json_invalid_raises(self):
        """无法提取时抛出 ValueError。"""
        with pytest.raises(ValueError, match="无法从 LLM 响应中提取 JSON"):
            _extract_json("这不是JSON")


class TestGeneratePanelists:
    """测试嘉宾生成。"""

    @pytest.mark.asyncio
    async def test_generate_panelists_success(self):
        """成功生成嘉宾。"""
        mock_response = json.dumps({
            "host": {"name": "张主持", "title": "科技主持人", "stance": "中立"},
            "experts": [
                {"name": "李博士", "title": "AI研究员", "stance": "支持AI"},
                {"name": "王教授", "title": "计算机教授", "stance": "质疑AI"},
                {"name": "赵CTO", "title": "创业公司CTO", "stance": "务实派"},
                {"name": "陈总监", "title": "产品总监", "stance": "用户视角"},
            ],
        }, ensure_ascii=False)

        with patch("panel_studio.llm._call_llm", new_callable=AsyncMock, return_value=mock_response):
            result = await generate_panelists("AI的未来", expert_count=4)

        assert "host" in result
        assert len(result["experts"]) == 4
        assert result["host"]["name"] == "张主持"

    @pytest.mark.asyncio
    async def test_generate_panelists_expert_count_mismatch(self):
        """专家数量不匹配时抛出异常。"""
        mock_response = json.dumps({
            "host": {"name": "张主持", "title": "主持人", "stance": "中立"},
            "experts": [{"name": "李博士", "title": "AI研究员", "stance": "支持"}],
        })

        with patch("panel_studio.llm._call_llm", new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(ValueError, match="专家数量不匹配"):
                await generate_panelists("AI", expert_count=4)


class TestGenerateSpeech:
    """测试发言生成。"""

    @pytest.mark.asyncio
    async def test_generate_host_opening(self):
        """生成主持人开场白。"""
        mock_response = "大家好，欢迎来到今天的圆桌讨论。"

        with patch("panel_studio.llm._call_llm", new_callable=AsyncMock, return_value=mock_response):
            result = await generate_speech(
                role="host",
                panelist={"name": "张主持", "title": "主持人"},
                topic="AI的未来",
                transcript="",
                speech_type="open",
            )

        assert "欢迎" in result or len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_expert_comment(self):
        """生成专家评论。"""
        mock_response = "我认为AI会改变很多行业，但不会完全取代人类。"

        with patch("panel_studio.llm._call_llm", new_callable=AsyncMock, return_value=mock_response):
            result = await generate_speech(
                role="expert",
                panelist={"name": "李博士", "title": "AI研究员", "stance": "支持AI"},
                topic="AI的未来",
                transcript="张主持：大家好\n",
                speech_type="comment",
            )

        assert len(result) > 0


class TestExtractFindings:
    """测试共识/分歧提取。"""

    @pytest.mark.asyncio
    async def test_extract_findings_success(self):
        """成功提取共识和分歧。"""
        mock_response = json.dumps({
            "consensus": ["AI是工具而非替代品", "需要加强AI监管"],
            "disagreement": ["AI是否会大规模取代工作岗位"],
        }, ensure_ascii=False)

        with patch("panel_studio.llm._call_llm", new_callable=AsyncMock, return_value=mock_response):
            result = await extract_findings("AI的未来", "讨论记录...")

        assert len(result["consensus"]) == 2
        assert len(result["disagreement"]) == 1

    @pytest.mark.asyncio
    async def test_extract_findings_empty(self):
        """空讨论返回空结果。"""
        mock_response = '{"consensus": [], "disagreement": []}'

        with patch("panel_studio.llm._call_llm", new_callable=AsyncMock, return_value=mock_response):
            result = await extract_findings("test", "test")

        assert result["consensus"] == []
        assert result["disagreement"] == []

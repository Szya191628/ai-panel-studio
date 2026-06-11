"""LLM 调用层 — Deepseek V4 Pro API 封装。

职责：
1. 嘉宾生成（主持人 + 专家阵容）
2. 发言生成（开场/追问/反驳/总结）
3. 共识/分歧提取

所有方法返回 dict，异常在边界捕获。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from panel_studio.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

logger = logging.getLogger(__name__)

# 超时配置
LLM_TIMEOUT = 60.0
LLM_STREAM_TIMEOUT = 120.0


async def _call_llm(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.8,
    max_tokens: int = 2000,
    stream: bool = False,
) -> str | Any:
    """调用 Deepseek API。

    Args:
        messages: 对话消息列表
        temperature: 温度参数
        max_tokens: 最大生成 token 数
        stream: 是否流式返回

    Returns:
        非流式：完整响应文本
        流式：httpx.Response 对象（供调用方迭代 SSE）
    """
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY 未配置，请在 .env 文件中设置")

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }

    async with httpx.AsyncClient(timeout=LLM_STREAM_TIMEOUT if stream else LLM_TIMEOUT) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()

        if stream:
            return resp  # 返回 response 对象，调用方迭代 SSE

        data = resp.json()
        return data["choices"][0]["message"]["content"]


def _extract_json(text: str) -> Any:
    """从 LLM 响应中提取 JSON（兼容 markdown code block）。"""
    # 尝试直接解析
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 块
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 尝试提取第一个 JSON 对象或数组
    for pattern in [r"(\{.*\})", r"(\[.*\])"]:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    raise ValueError(f"无法从 LLM 响应中提取 JSON: {text[:200]}")


# ============================================================
# 嘉宾生成
# ============================================================

PANELIST_GENERATION_PROMPT = """你是一个专业的节目策划人。请为以下讨论话题生成一组圆桌讨论嘉宾。

话题：{topic}
需要生成：1位主持人 + {expert_count}位专家

要求：
1. 主持人：经验丰富、善于引导讨论，立场中立
2. 专家：来自不同背景和立场，观点有差异性，能产生碰撞
3. 每位嘉宾需要：name（中文姓名）、title（职业/Title，简短）、stance（立场描述，1句话）
4. 嘉宾姓名要有真实感，不要用"专家A"这种泛称

请严格返回以下 JSON 格式，不要有其他文字：
{{
  "host": {{
    "name": "姓名",
    "title": "职业/Title",
    "stance": "立场描述"
  }},
  "experts": [
    {{
      "name": "姓名",
      "title": "职业/Title",
      "stance": "立场描述"
    }}
  ]
}}"""


async def generate_panelists(topic: str, expert_count: int = 4) -> dict[str, Any]:
    """调用 LLM 生成嘉宾阵容。

    Returns:
        {"host": {...}, "experts": [{...}, ...]}
    """
    prompt = PANELIST_GENERATION_PROMPT.format(topic=topic, expert_count=expert_count)
    messages = [{"role": "user", "content": prompt}]

    raw = await _call_llm(messages, temperature=0.9, max_tokens=1500)
    result = _extract_json(raw)

    # 验证结构
    if "host" not in result or "experts" not in result:
        raise ValueError("LLM 返回的嘉宾数据结构不完整")
    if not isinstance(result["experts"], list) or len(result["experts"]) != expert_count:
        raise ValueError(f"专家数量不匹配：期望 {expert_count}，实际 {len(result['experts'])}")

    return result


# ============================================================
# 发言生成
# ============================================================

SPEECH_SYSTEM_PROMPT = """你是一个圆桌讨论的 AI 引擎。你需要模拟嘉宾在讨论中的发言。

规则：
1. 每次发言控制在 1-3 句话，简洁有力
2. 发言要体现嘉宾的立场和专业背景
3. 可以引用或反驳其他嘉宾的观点
4. 保持自然的口语化表达，不要过于书面化
5. 不要使用 JSON 或结构化格式，直接输出发言内容"""


HOST_OPENING_PROMPT = """你是主持人 {host_name}（{host_title}）。
讨论话题：{topic}
嘉宾阵容：{panelists_info}

请用 2-3 句话做开场白，介绍话题和嘉宾，引导讨论开始。"""


HOST追问_PROMPT = """你是主持人 {host_name}（{host_title}）。
讨论话题：{topic}

当前讨论记录：
{transcript}

请针对讨论中的某个观点进行追问或引导深入，1-2句话。"""


HOST总结_PROMPT = """你是主持人 {host_name}（{host_title}）。
讨论话题：{topic}

完整讨论记录：
{transcript}

请用 3-5 句话做讨论总结，概括主要观点、共识和分歧，给出建设性结论。"""


EXPERT_SPEECH_PROMPT = """你是 {name}（{title}），立场：{stance}。
讨论话题：{topic}

当前讨论记录：
{transcript}

请发表你的观点（1-2句话）。可以：
- 提出新观点
- 补充或支持某位嘉宾的观点
- 反驳某位嘉宾的观点
- 回应主持人的提问"""


async def generate_speech(
    *,
    role: str,
    panelist: dict[str, str],
    topic: str,
    transcript: str,
    speech_type: str = "comment",
    host_info: dict[str, str] | None = None,
) -> str:
    """生成单次发言。

    Args:
        role: "host" 或 "expert"
        panelist: 当前发言嘉宾信息
        topic: 讨论话题
        transcript: 当前讨论记录
        speech_type: 发言类型
        host_info: 主持人信息（主持人发言时使用）

    Returns:
        发言内容字符串
    """
    if role == "host":
        host = host_info or panelist
        if speech_type == "open":
            prompt = HOST_OPENING_PROMPT.format(
                host_name=host["name"], host_title=host["title"],
                topic=topic,
                panelists_info="",  # 由调用方填充
            )
        elif speech_type == "summary":
            prompt = HOST总结_PROMPT.format(
                host_name=host["name"], host_title=host["title"],
                topic=topic, transcript=transcript,
            )
        else:
            prompt = HOST追问_PROMPT.format(
                host_name=host["name"], host_title=host["title"],
                topic=topic, transcript=transcript,
            )
    else:
        prompt = EXPERT_SPEECH_PROMPT.format(
            name=panelist["name"], title=panelist["title"],
            stance=panelist.get("stance", ""),
            topic=topic, transcript=transcript,
        )

    messages = [
        {"role": "system", "content": SPEECH_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    return await _call_llm(messages, temperature=0.85, max_tokens=300)


# ============================================================
# 共识/分歧提取
# ============================================================

FINDINGS_PROMPT = """分析以下圆桌讨论记录，提取共识点和分歧点。

讨论话题：{topic}

讨论记录：
{transcript}

请返回 JSON 格式：
{{
  "consensus": ["共识点1", "共识点2"],
  "disagreement": ["分歧点1", "分歧点2"]
}}

要求：
1. 每个要点用一句话概括
2. 共识：多位嘉宾明确同意的观点
3. 分歧：嘉宾之间存在明显不同看法的地方
4. 如果某个类别没有，返回空数组"""


async def extract_findings(
    topic: str,
    transcript: str,
) -> dict[str, list[str]]:
    """从讨论记录中提取共识和分歧。

    Returns:
        {"consensus": [...], "disagreement": [...]}
    """
    prompt = FINDINGS_PROMPT.format(topic=topic, transcript=transcript)
    messages = [{"role": "user", "content": prompt}]

    raw = await _call_llm(messages, temperature=0.3, max_tokens=1000)
    result = _extract_json(raw)

    # 确保返回结构正确
    return {
        "consensus": result.get("consensus", []),
        "disagreement": result.get("disagreement", []),
    }


# ============================================================
# 下一位发言者决策
# ============================================================

NEXT_SPEAKER_PROMPT = """你是一个圆桌讨论的调度器。根据当前讨论状态，决定下一位发言者。

讨论话题：{topic}

当前讨论记录：
{transcript}

可选的下一位发言者（排除上一位发言者）：
{candidates}

请返回 JSON 格式，选择最适合下一位发言的嘉宾：
{{
  "next_speaker": "嘉宾姓名",
  "reason": "简短理由（10字以内）"
}}

选择标准：
1. 如果主持人刚做完开场，选择立场最强的专家先发言
2. 如果有嘉宾被点名或被反驳，优先让该嘉宾回应
3. 避免连续发言，保持讨论多样性
4. 优先选择还没发言或发言较少的嘉宾"""


async def decide_next_speaker(
    topic: str,
    transcript: str,
    candidates: list[dict[str, str]],
    last_speaker: str | None = None,
) -> str:
    """决定下一位发言者。

    Args:
        topic: 讨论话题
        transcript: 当前讨论记录
        candidates: 候选嘉宾列表
        last_speaker: 上一位发言者姓名

    Returns:
        下一位发言者的姓名
    """
    if len(candidates) == 1:
        return candidates[0]["name"]

    candidates_info = "\n".join(
        f"- {c['name']}（{c['title']}）- 立场：{c.get('stance', '未知')}"
        for c in candidates
    )

    prompt = NEXT_SPEAKER_PROMPT.format(
        topic=topic, transcript=transcript, candidates=candidates_info,
    )
    messages = [{"role": "user", "content": prompt}]

    raw = await _call_llm(messages, temperature=0.5, max_tokens=200)
    result = _extract_json(raw)

    next_name = result.get("next_speaker", "")
    # 验证返回的姓名在候选列表中
    valid_names = {c["name"] for c in candidates}
    if next_name not in valid_names:
        # fallback: 随机选择
        import random
        next_name = random.choice(candidates)["name"]

    return next_name

# AI Panel Studio

**AI圆桌讨论演播厅** — 让任何人都能瞬间召集一支"虚拟智库"，围绕任意议题展开深度碰撞。

## 快速开始

### 环境要求

- Python 3.10+
- Deepseek API Key

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd ai-panel-studio

# 安装依赖
pip install -e ".[dev]"
```

### 配置

创建 `.env` 文件或设置环境变量：

```bash
# Deepseek API 配置
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_BASE_URL=https://api.openai-proxy.org/v1
DEEPSEEK_MODEL=deepseek-v4-flash

# 服务配置（可选）
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

### 启动

```bash
# 写入样例数据（可选）
python scripts/seed_data.py

# 启动服务
python -m panel_studio.app
```

访问 http://localhost:8000 开始使用。

### 运行测试

```bash
pytest tests/ -v
```

## 功能特性

| 功能 | 说明 |
|------|------|
| 🎙️ 嘉宾生成 | 输入话题+人数，AI动态生成主持人+专家阵容 |
| 🎭 演播厅模式 | 主持人开场/追问/串联/总结，专家自主发言/反驳/补充 |
| 👥 嘉宾状态小窗 | 实时显示Agent运行状态（待机/准备发言/发言中） |
| ✅ 共识/分歧 | 讨论过程中持续提炼，实时更新 |
| 💬 实时Transcript | SSE推送，逐条显示发言 |
| 📊 多讨论并行 | 不同讨论状态、事件流、transcript互相隔离 |

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 后端 | FastAPI + uvicorn | 异步框架，原生SSE支持 |
| 数据库 | SQLite (WAL) | 零依赖，参考agent-roundtable |
| 前端 | 原生HTML/CSS/JS | 零构建步骤，CDN加载字体 |
| 实时推送 | SSE (StreamingResponse) | 基于asyncio.Queue |
| LLM | Deepseek V4 Pro | 通过httpx异步调用 |

## 项目结构

```
ai-panel-studio/
├── src/panel_studio/
│   ├── app.py           # FastAPI应用入口
│   ├── config.py        # 配置管理
│   ├── core.py          # 业务逻辑层
│   ├── db.py            # 数据库访问层
│   ├── llm.py           # LLM调用封装
│   ├── models.py        # Pydantic数据模型
│   ├── schema.py        # SQLite DDL + 迁移
│   ├── sse.py           # SSE事件管理
│   └── static/          # 前端文件
├── tests/               # 测试代码
├── scripts/             # 工具脚本
└── docs/                # 文档
```

## API 列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 首页 |
| GET | `/studio/{id}` | 演播厅页面 |
| GET | `/api/discussions` | 讨论列表 |
| POST | `/api/discussions` | 创建讨论 |
| GET | `/api/discussions/{id}` | 讨论详情 |
| POST | `/api/discussions/{id}/panelists/generate` | AI生成嘉宾 |
| POST | `/api/discussions/{id}/confirm` | 确认嘉宾 |
| POST | `/api/discussions/{id}/start` | 开始讨论 |
| POST | `/api/discussions/{id}/stop` | 结束讨论 |
| GET | `/api/discussions/{id}/events` | SSE事件流 |

## 开发范式

本项目严格遵循 SDD → DDD → TDD 的多范式融合开发：

1. **SDD（契约/模型驱动）**: 先定义 Pydantic 模型和 SQLite Schema，再写业务代码
2. **DDD（设计驱动）**: 以演播厅视觉风格驱动前端组件和状态流转
3. **TDD（测试驱动）**: 核心逻辑先写测试再实现，49个测试用例全部通过

## 许可证

Apache-2.0

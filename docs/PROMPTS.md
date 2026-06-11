# 核心 Prompt 记录文档（25 段）

> 本文档记录引导 AI 开发 AI Panel Studio 的最核心原始 Prompt，按四大阶段分类。
> 每段 Prompt 后附注释说明编写意图、遇到的问题及修正手段。

---

## 一、SDD 阶段（契约/模型驱动）— 6 段

### Prompt 1 — 项目初始化与技术选型

```
读取项目架构，确保每个模块完成后进行 code review 并测试功能正常后提交 git。
后端使用 FastAPI，前端使用原生 HTML/CSS/JS，数据库使用 SQLite。
项目创建在 D:\ai-panel-studio 目录。
```

> **意图**：确定技术栈和项目规范，避免后续返工。
> **问题**：需要明确目录结构避免混乱。
> **修正**：补充了参考 agent-roundtable 的架构模式。

---

### Prompt 2 — 数据模型定义

```
SDD 阶段核心产物：所有实体在此定义，schema.py 和 db.py 对齐此模型。
定义 Discussion、Panelist、Speech、Finding 四个核心实体，
使用 Pydantic BaseModel，字段包含 id、topic、status、expert_count 等。
```

> **意图**：先定义数据契约，再写业务代码，确保前后端对齐。
> **问题**：Pydantic v2 的语法与 v1 不同。
> **修正**：明确使用 `from pydantic import BaseModel, Field`。

---

### Prompt 3 — SQLite Schema 设计

```
参考 agent-roundtable 的 schema 模式：
- 单一 SCHEMA_SQL 字符串
- CREATE TABLE IF NOT EXISTS 幂等执行
- PRAGMA user_version 版本迁移
- CHECK 约束 + Python 端双重验证
定义 discussions、panelists、speeches、findings 四张表。
```

> **意图**：复用成熟的 Schema 管理模式，保证数据一致性。
> **问题**：SQLite 不支持 `ALTER TABLE MODIFY COLUMN`。
> **修正**：预留迁移系统，使用 `PRAGMA user_version` 版本控制。

---

### Prompt 4 — 数据库访问层

```
数据库访问层 — SQLite CRUD 操作。
所有方法返回 dict（JSON-serializable），遵循 agent-roundtable 的 db.py 模式。
包含 Discussion/Panelist/Speech/Finding 的完整 CRUD。
```

> **意图**：统一封装数据库操作，业务层不直接写 SQL。
> **问题**：返回类型需要一致。
> **修正**：所有方法返回 `dict[str, Any]`，异常用 `raise ValueError`。

---

### Prompt 5 — API 契约文档

```
创建 docs/API.md，定义所有 API 端点：
GET /api/discussions — 列出讨论
POST /api/discussions — 创建讨论
POST /api/discussions/{id}/panelists/generate — AI 生成嘉宾
POST /api/discussions/{id}/confirm — 确认嘉宾
POST /api/discussions/{id}/start — 开始讨论
POST /api/discussions/{id}/stop — 结束讨论
GET /api/discussions/{id}/events — SSE 事件流
包含请求/响应示例。
```

> **意图**：先定义 API 契约，前端和后端并行开发。
> **问题**：SSE 端点的事件类型需要明确定义。
> **修正**：补充了 7 种 SSE 事件类型及数据结构。

---

### Prompt 6 — 配置管理

```
配置管理 — 从环境变量读取所有配置项。
使用 python-dotenv，包含 DEEPSEEK_API_KEY、DEEPSEEK_BASE_URL、
DEEPSEEK_MODEL、HOST、PORT、DB_PATH 等配置。
API Key 默认值从 .env 读取，不硬编码。
```

> **意图**：敏感信息不入代码库，通过环境变量注入。
> **问题**：需要提供默认值方便开发。
> **修正**：提供 `.env.example` 模板文件。

---

## 二、DDD 阶段（设计驱动）— 7 段

### Prompt 7 — 设计 Token 系统

```
创建 static/css/theme.css，定义演播厅视觉系统：
- 暗色背景色系（--bg-primary: #0a0e1a）
- 嘉宾色板 8 色（--guest-1 到 --guest-8）
- 状态色（idle/preparing/speaking）
- 圆角、阴影、字体、过渡等设计 Token
参考 agent-roundtable 的 CSS Custom Properties 模式。
```

> **意图**：统一设计语言，所有组件引用 Token 而非硬编码颜色。
> **问题**：需要兼顾暗色主题的可读性。
> **修正**：文字使用高对比度色（#f1f5f9），辅助文字用中等亮度。

---

### Prompt 8 — 首页设计与实现

```
创建 index.html + index.css，首页功能：
- 暗色演播厅风格
- 讨论列表（卡片式，显示状态、话题、嘉宾数、创建时间）
- "新建讨论"按钮 → 弹窗输入话题+专家人数
- 响应式布局（CSS Grid，auto-fill minmax(320px, 1fr)）
```

> **意图**：首页是用户第一印象，需要沉浸式演播厅氛围。
> **问题**：卡片 hover 效果需要流畅。
> **修正**：使用 `transform: translateY(-2px)` + `box-shadow` 组合。

---

### Prompt 9 — 演播厅布局设计

```
演播厅页面 studio.html + studio.css，三栏布局：
- 左侧（280px）：嘉宾状态小窗
- 中间（1fr）：Transcript 发言流
- 右侧（300px）：共识/分歧区
使用 CSS Grid，各区域独立滚动（overflow-y: auto）。
不依赖页面整体滚动。
```

> **意图**：沉浸式演播厅体验，信息密度高但不混乱。
> **问题**：窄屏需要适配。
> **修正**：添加媒体查询，<1200px 隐藏右栏，<768px 单栏。

---

### Prompt 10 — 嘉宾状态小窗组件

```
嘉宾状态小窗 panelist-card：
- 左边框 3px 色条（--guest-color）
- 头像圆形（背景色=嘉宾色，首字白色）
- 状态指示灯（idle灰/preparing黄/speaking绿，带脉冲动画）
- 姓名、Title、立场、当前关注点
- speaking 状态时卡片边框高亮
```

> **意图**：实时反映 Agent 运行状态，增强沉浸感。
> **问题**：状态指示灯需要动画但不能太抢眼。
> **修正**：使用 `@keyframes pulse` 控制透明度变化。

---

### Prompt 11 — Transcript 发言流设计

```
发言气泡 speech-item：
- 左侧头像圆形（背景色=嘉宾色）
- 右侧气泡（背景色=--bg-card，左边框 3px 嘉宾色）
- 主持人气泡特殊样式（蓝色半透明背景）
- 新发言 fadeInUp 动画入场
- 发言类型标签（开场/观点/反驳/提问/总结）
```

> **意图**：发言流是演播厅核心，需要清晰的视觉层次。
> **问题**：气泡样式需要区分主持人和专家。
> **修正**：主持人使用 `.speech-item.host` 特殊样式。

---

### Prompt 12 — 前端 JavaScript 逻辑

```
创建三个 JS 文件：
- utils.js：API 请求、escapeHtml、格式化工具函数
- index.js：首页逻辑（加载列表、创建讨论、模态框控制）
- studio.js：演播厅逻辑（SSE连接、实时渲染、状态管理）
使用全局 state 对象管理状态，无框架依赖。
```

> **意图**：零构建步骤，纯原生 JS，降低部署复杂度。
> **问题**：SSE 重连需要指数退避。
> **修正**：EventSource 内置重连机制，添加 `onerror` 日志。

---

### Prompt 13 — 嘉宾确认弹窗

```
嘉宾确认弹窗 config-overlay：
- 全屏半透明遮罩 + 毛玻璃效果
- 嘉宾卡片网格预览（带角色标签）
- 底部操作栏：重新生成（幽灵风格）+ 确认进入（渐变强调色）
- 重新生成 hover 时图标旋转 180°
- 确认按钮 hover 时箭头右移 3px 引导点击
```

> **意图**：确认环节是用户决策点，需要清晰的行动引导。
> **问题**：两个按钮的视觉权重需要合理分配。
> **修正**：确认按钮用渐变+阴影强调，重新生成用透明边框弱化。

---

## 三、TDD 阶段（测试驱动）— 7 段

### Prompt 14 — 测试 Fixtures 设计

```
创建 tests/conftest.py，定义测试 Fixtures：
- db：临时数据库实例（tmp_path）
- conn：数据库连接（自动关闭）
- sample_discussion：样例讨论
- sample_panelists：样例嘉宾（1主持+4专家）
使用 pytest tmp_path 隔离测试数据。
```

> **意图**：测试数据隔离，每个测试用例独立数据库。
> **问题**：需要确保连接正确关闭。
> **修正**：使用 `yield` + `finally` 模式。

---

### Prompt 15 — Schema 测试

```
创建 tests/test_schema.py：
- test_schema_creates_tables：验证 4 张表创建
- test_schema_idempotent：重复执行不报错
- test_indexes_created：验证 3 个索引创建
- test_discussion_status_constraint：无效状态抛 IntegrityError
- test_panelist_role_constraint：无效角色抛 IntegrityError
- test_expert_count_range：人数越界抛 IntegrityError
```

> **意图**：Schema 是数据层基础，必须严格验证约束。
> **问题**：SQLite CHECK 约束的错误类型是 IntegrityError。
> **修正**：使用 `pytest.raises(sqlite3.IntegrityError)`。

---

### Prompt 16 — 数据库 CRUD 测试

```
创建 tests/test_db.py，覆盖所有 CRUD 操作：
- Discussion：创建/获取/列表/过滤/状态更新
- Panelist：添加/无效角色/排序/状态更新/清除
- Speech：添加/空内容/无效类型/排序/按轮次过滤/当前轮次
- Finding：添加/无效类型/按类型过滤
```

> **意图**：数据库层是业务基础，CRUD 必须 100% 正确。
> **问题**：列表排序测试因时间戳相同失败。
> **修正**：添加 `time.sleep(0.01)` 确保时间戳不同。

---

### Prompt 17 — LLM 调用测试（Mock）

```
创建 tests/test_llm.py，使用 unittest.mock 隔离 LLM 调用：
- TestExtractJson：直接JSON/code block提取/混合文本/数组/无效输入
- TestGeneratePanelists：成功/专家数量不匹配
- TestGenerateSpeech：主持人开场/专家评论
- TestExtractFindings：成功提取/空讨论
```

> **意图**：LLM 调用不稳定，必须用 Mock 确保测试可重复。
> **问题**：需要模拟 httpx 异步调用。
> **修正**：使用 `@patch("panel_studio.llm._call_llm", new_callable=AsyncMock)`。

---

### Prompt 18 — API 端点测试

```
创建 tests/test_api.py，使用 FastAPI TestClient：
- test_index_returns_html：首页返回 HTML
- test_create_discussion：创建讨论成功
- test_create_discussion_empty_topic：空话题返回 400
- test_create_discussion_invalid_expert_count：无效人数返回 400
- test_list_discussions：列表返回正确数量
- test_get_discussion：详情返回完整数据
- test_get_discussion_not_found：不存在返回 404
- test_studio_page：演播厅页面返回 HTML
```

> **意图**：API 是前后端契约，必须验证端点行为。
> **问题**：TestClient 的数据库需要与应用隔离。
> **修正**：使用 monkeypatch 重定向 DB_PATH 到 tmp_path。

---

### Prompt 19 — JSON 提取逻辑测试

```
_extract_json 函数需要兼容多种 LLM 输出格式：
- 纯 JSON 字符串
- ```json ... ``` markdown code block
- 混合文本中的 JSON 对象
- JSON 数组
- 无法提取时抛出 ValueError
```

> **意图**：LLM 输出格式不稳定，提取逻辑必须健壮。
> **问题**：正则匹配需要兼容换行符。
> **修正**：使用 `re.DOTALL` 标志让 `.` 匹配换行。

---

### Prompt 20 — 测试运行与验证

```
运行全部测试并确保通过：
python -m pytest tests/ -v --tb=short
预期：49 passed
如果有失败，分析原因并修复。
```

> **意图**：测试是质量门禁，必须全部通过才能提交。
> **问题**：Windows 控制台中文编码导致输出乱码。
> **修正**：测试逻辑正确即可，控制台编码不影响测试结果。

---

## 四、E2E 阶段（端到端质量闭环）— 5 段

### Prompt 21 — FastAPI 应用集成

```
创建 app.py，集成所有模块：
- FastAPI 应用 + CORS 中间件
- 页面路由：GET /、GET /studio/{id}
- API 路由：CRUD + 嘉宾生成 + SSE
- 静态文件服务（StaticFiles）
- 异步任务（asyncio.create_task 启动讨论引擎）
```

> **意图**：将所有模块组装为可运行的应用。
> **问题**：异步任务需要不阻塞请求。
> **修正**：使用 `asyncio.create_task` 启动讨论引擎。

---

### Prompt 22 — SSE 事件流实现

```
创建 sse.py，实现 SSE 事件管理：
- SSEManager：管理多讨论的订阅者
- subscribe/unsubscribe：订阅/取消订阅
- publish：发布事件到所有订阅者
- stream：生成 SSE 事件流（用于 StreamingResponse）
- 心跳：30秒超时发送心跳
```

> **意图**：实时推送是演播厅核心体验。
> **问题**：需要支持多客户端订阅同一讨论。
> **修正**：每个讨论维护一个 Queue 集合。

---

### Prompt 23 — 讨论引擎实现

```
创建 core.py 中的 run_discussion 方法，实现讨论驱动引擎：
1. 主持人开场（speech_type=open）
2. 循环：专家发言 → 提取共识/分歧 → 判断是否继续
3. 主持人总结（speech_type=summary）
4. 结束讨论（生成简短结论）
关键：不是轮流发言，而是通过 LLM 决定下一位发言者。
```

> **意图**：模拟真实讨论节奏，非机械轮流。
> **问题**：需要控制讨论长度防止无限循环。
> **修正**：设置 MAX_ROUNDS=5 和 MAX_SPEECHES_PER_ROUND=12。

---

### Prompt 24 — 样例数据脚本

```
创建 scripts/seed_data.py，预设 5 条高质量讨论：
1. "AI是否会取代程序员？"（4人）
2. "远程办公 vs 现场办公"（3人）
3. "新能源汽车的技术路线之争"（4人）
4. "教育内卷的根源与出路"（3人）
5. "Web3是否还有未来？"（4人）
每条包含完整的主持人+专家阵容（姓名、Title、立场）。
```

> **意图**：提供开箱即用的演示数据，降低体验门槛。
> **问题**：嘉宾姓名需要有真实感。
> **修正**：使用中文常见姓名组合，避免"专家A"等泛称。

---

### Prompt 25 — Bug 修复与质量闭环

```
修复两个运行时 Bug：
1. escapeHtml is not defined — utils.js 缺少该函数定义
   修复：添加 escapeHtml 函数到 utils.js
2. 结束讨论 Internal Server Error — 前端无 body 的 POST 请求
   导致 request.json() 崩溃
   修复：添加 try-except 包裹 JSON 解析
```

> **意图**：真实运行中发现的问题，需要快速定位和修复。
> **问题**：Bug 1 是函数定义遗漏，Bug 2 是异常处理缺失。
> **修正**：建立"发现问题 → 定位原因 → 修复 → 验证 → 提交"闭环。

---

## 附：Prompt 编写原则总结

| 原则 | 说明 |
|------|------|
| **明确产出物** | 每段 Prompt 明确指定文件名和内容要求 |
| **参考已有架构** | 引用 agent-roundtable 的模式，减少歧义 |
| **分层递进** | SDD→DDD→TDD→E2E，每层依赖前一层 |
| **测试先行** | 先定义测试预期，再实现功能 |
| **及时修复** | 发现问题立即修复并提交，不积累技术债 |

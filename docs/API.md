# API 契约文档

## 基础信息

- Base URL: `http://localhost:8000`
- Content-Type: `application/json`
- 所有响应均为 JSON 格式

## 页面路由

### GET /

首页，返回 HTML 页面。

### GET /studio/{discussion_id}

演播厅页面，返回 HTML 页面。

## API 端点

### GET /api/discussions

列出所有讨论。

**查询参数：**
- `status` (可选): 按状态过滤 (configuring/active/concluded)

**响应：**
```json
{
  "ok": true,
  "discussions": [
    {
      "id": "abc123",
      "topic": "AI是否会取代程序员？",
      "status": "configuring",
      "expert_count": 4,
      "created_at": 1718000000.0,
      "concluded_at": null,
      "conclusion": null
    }
  ],
  "count": 1
}
```

---

### POST /api/discussions

创建新讨论。

**请求体：**
```json
{
  "topic": "AI是否会取代程序员？",
  "expert_count": 4
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| topic | string | ✅ | 讨论话题 (1-200字) |
| expert_count | int | ❌ | 专家人数 (2-8, 默认4) |

**响应：**
```json
{
  "ok": true,
  "discussion": {
    "id": "abc123",
    "topic": "AI是否会取代程序员？",
    "status": "configuring",
    "expert_count": 4,
    "created_at": 1718000000.0
  }
}
```

---

### GET /api/discussions/{discussion_id}

获取讨论详情（含嘉宾、发言、发现）。

**响应：**
```json
{
  "ok": true,
  "discussion": { ... },
  "panelists": [
    {
      "id": 1,
      "discussion_id": "abc123",
      "name": "张主持",
      "title": "资深科技主持人",
      "stance": "中立引导",
      "color": "#3b82f6",
      "role": "host",
      "status": "idle",
      "focus": null
    }
  ],
  "speeches": [ ... ],
  "findings": [ ... ]
}
```

---

### POST /api/discussions/{discussion_id}/panelists/generate

AI 生成嘉宾阵容。

**响应：**
```json
{
  "ok": true,
  "panelists": [
    {
      "id": 1,
      "name": "张主持",
      "title": "资深科技主持人",
      "stance": "中立引导",
      "color": "#3b82f6",
      "role": "host"
    },
    {
      "id": 2,
      "name": "李博士",
      "title": "AI研究员",
      "stance": "AI将增强而非取代",
      "color": "#ef4444",
      "role": "expert"
    }
  ]
}
```

---

### POST /api/discussions/{discussion_id}/confirm

确认嘉宾阵容，进入演播厅。

**响应：**
```json
{
  "ok": true,
  "discussion": { ... },
  "panelists": [ ... ]
}
```

---

### POST /api/discussions/{discussion_id}/start

启动讨论引擎（异步）。

**响应：**
```json
{
  "ok": true,
  "message": "讨论引擎已启动"
}
```

---

### POST /api/discussions/{discussion_id}/stop

结束讨论。

**请求体（可选）：**
```json
{
  "conclusion": "自定义结论"
}
```

**响应：**
```json
{
  "ok": true,
  "discussion": { ... }
}
```

---

### GET /api/discussions/{discussion_id}/events

SSE 事件流。

**事件类型：**

| 事件 | 说明 | 数据 |
|------|------|------|
| `init` | 初始状态 | 完整讨论数据 |
| `panelists_generated` | 嘉宾生成完成 | `{panelists: [...]}` |
| `status_changed` | 状态变更 | `{status: "active"}` |
| `panelist_update` | 嘉宾状态更新 | `{panelist_id, status, focus}` |
| `speech` | 新发言 | 完整发言对象 |
| `finding` | 新发现 | `{type, content, round_num}` |
| `concluded` | 讨论结束 | `{conclusion}` |
| `error` | 错误 | `{error}` |

## 错误响应

所有错误返回标准 HTTP 状态码 + JSON：

```json
{
  "detail": "错误描述"
}
```

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

# 数据模型 ER 图

## 实体关系图

```mermaid
erDiagram
    Discussion ||--o{ Panelist : "拥有"
    Discussion ||--o{ Speech : "包含"
    Discussion ||--o{ Finding : "产生"
    Panelist ||--o{ Speech : "发表"

    Discussion {
        string id PK "唯一标识"
        string topic "讨论话题"
        string status "configuring|active|concluded"
        int expert_count "专家人数(2-8)"
        float created_at "创建时间戳"
        float concluded_at "结束时间戳"
        string conclusion "讨论结论"
    }

    Panelist {
        int id PK "自增ID"
        string discussion_id FK "所属讨论"
        string name "姓名"
        string title "职业/Title"
        string stance "立场描述"
        string color "专属颜色(十六进制)"
        string role "host|expert"
        string status "idle|preparing|speaking"
        string focus "当前关注点"
    }

    Speech {
        int id PK "自增ID"
        string discussion_id FK "所属讨论"
        int panelist_id FK "发言嘉宾"
        string content "发言内容"
        string speech_type "open|comment|rebut|question|summary"
        int round_num "轮次"
        float created_at "时间戳"
    }

    Finding {
        int id PK "自增ID"
        string discussion_id FK "所属讨论"
        string type "consensus|disagreement"
        string content "内容"
        int round_num "轮次"
    }
```

## 状态机

```mermaid
stateDiagram-v2
    [*] --> configuring : 创建讨论
    configuring --> active : 确认嘉宾
    active --> concluded : 讨论结束
    configuring --> concluded : 取消

    state configuring {
        [*] --> 生成嘉宾
        生成嘉宾 --> 确认阵容
    }

    state active {
        [*] --> 主持人开场
        主持人开场 --> 专家发言
        专家发言 --> 提取共识分歧
        提取共识分歧 --> 专家发言
        专家发言 --> 主持人总结
    }
```

## 索引

| 索引名 | 表 | 列 | 用途 |
|--------|-----|-----|------|
| idx_panelists_discussion | panelists | discussion_id | 按讨论查嘉宾 |
| idx_speeches_discussion | speeches | discussion_id | 按讨论查发言 |
| idx_speeches_round | speeches | discussion_id, round_num | 按轮次查发言 |
| idx_findings_discussion | findings | discussion_id | 按讨论查发现 |

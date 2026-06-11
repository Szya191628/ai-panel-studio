"""样例数据脚本 — 预设5条讨论话题与嘉宾阵容。"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from panel_studio.db import PanelDB
from panel_studio.schema import PANEL_COLORS

# 5条预设讨论话题
SEED_DATA = [
    {
        "topic": "AI是否会取代程序员？",
        "expert_count": 4,
        "panelists": {
            "host": {"name": "张明远", "title": "资深科技主持人", "stance": "中立引导，追问本质"},
            "experts": [
                {"name": "李博涵", "title": "AI研究员", "stance": "AI将增强而非取代程序员，工具链升级是必然"},
                {"name": "王铁军", "title": "资深后端架构师", "stance": "AI会取代大部分重复编码工作，架构师不可替代"},
                {"name": "赵学礼", "title": "计算机科学教授", "stance": "编程本质是思维训练，AI无法替代创造性思考"},
                {"name": "陈思远", "title": "创业公司CTO", "stance": "AI将重塑整个软件工程范式，10x工程师将被重新定义"},
            ],
        },
    },
    {
        "topic": "远程办公 vs 现场办公：未来工作模式之争",
        "expert_count": 3,
        "panelists": {
            "host": {"name": "林小雅", "title": "职场观察家", "stance": "关注数据与趋势，不预设立场"},
            "experts": [
                {"name": "吴志强", "title": "人力资源总监", "stance": "远程办公降低协作效率，文化凝聚力难以远程建立"},
                {"name": "周云飞", "title": "远程工作倡导者", "stance": "远程办公是未来趋势，异步协作提升深度工作质量"},
                {"name": "黄明哲", "title": "组织行为学教授", "stance": "混合办公是最优解，关键在于制度设计而非地点选择"},
            ],
        },
    },
    {
        "topic": "新能源汽车的技术路线之争：纯电 vs 氢能 vs 增程",
        "expert_count": 4,
        "panelists": {
            "host": {"name": "刘大伟", "title": "汽车媒体主编", "stance": "技术路线之争需要数据说话"},
            "experts": [
                {"name": "马电驰", "title": "电池技术专家", "stance": "纯电是终极方案，固态电池将解决续航焦虑"},
                {"name": "杨氢宇", "title": "氢能研究员", "stance": "氢能适合商用车和长途运输，纯电有天花板"},
                {"name": "钱程远", "title": "增程车主工程师", "stance": "增程是过渡期最优解，兼顾补能便利和用车成本"},
                {"name": "孙未来", "title": "汽车分析师", "stance": "技术路线不是非此即彼，场景决定方案"},
            ],
        },
    },
    {
        "topic": "教育内卷的根源与出路",
        "expert_count": 3,
        "panelists": {
            "host": {"name": "郑心怡", "title": "教育媒体人", "stance": "关注每个孩子的成长"},
            "experts": [
                {"name": "高育才", "title": "中学校长", "stance": "内卷根源在评价体系单一，改革需从高考入手"},
                {"name": "徐成长", "title": "家庭教育专家", "stance": "家长焦虑是内卷放大器，需要重建教育价值观"},
                {"name": "韩公平", "title": "教育经济学教授", "stance": "内卷本质是资源分配问题，供给侧改革才是出路"},
            ],
        },
    },
    {
        "topic": "Web3是否还有未来？",
        "expert_count": 4,
        "panelists": {
            "host": {"name": "何区块", "title": "科技播客主持人", "stance": "理性看待技术周期"},
            "experts": [
                {"name": "罗链上", "title": "区块链开发者", "stance": "Web3基础设施已成熟，杀手级应用即将出现"},
                {"name": "梁务实", "title": "风投合伙人", "stance": "Web3泡沫已破，但去中心化理念有长期价值"},
                {"name": "宋质疑", "title": "互联网产品经理", "stance": "Web3缺乏真实用户需求，是技术精英的自嗨"},
                {"name": "唐监管", "title": "金融科技研究员", "stance": "Web3需要合规框架，监管明朗后才有真正发展"},
            ],
        },
    },
]


def seed_database(db_path: str | None = None):
    """写入样例数据。"""
    db = PanelDB(db_path=db_path) if db_path else PanelDB()
    conn = db.connect()

    try:
        for item in SEED_DATA:
            # 创建讨论
            disc = db.create_discussion(
                conn,
                topic=item["topic"],
                expert_count=item["expert_count"],
            )
            did = disc["id"]

            # 添加主持人
            host_data = item["panelists"]["host"]
            db.add_panelist(
                conn,
                discussion_id=did,
                name=host_data["name"],
                title=host_data["title"],
                stance=host_data["stance"],
                color=PANEL_COLORS[0],
                role="host",
            )

            # 添加专家
            for i, exp_data in enumerate(item["panelists"]["experts"]):
                db.add_panelist(
                    conn,
                    discussion_id=did,
                    name=exp_data["name"],
                    title=exp_data["title"],
                    stance=exp_data["stance"],
                    color=PANEL_COLORS[(i + 1) % len(PANEL_COLORS)],
                    role="expert",
                )

            print(f"[OK] 已创建: {item['topic']}")

        print(f"\n[DONE] 成功写入 {len(SEED_DATA)} 条样例数据！")
    finally:
        conn.close()


if __name__ == "__main__":
    seed_database()

"""例 4：MCP 解决什么问题——一个 client 连两个 server。

跑法：
    python examples/ch3_concepts/e04_mcp.py

不启动真实进程，用类模拟 client/server 的消息往返。

这样你能看清"协议"到底传了什么，而不用先学会部署。
"""
from __future__ import annotations

import json
from typing import Any


# ══════════════════════════════════════════════════════════════════
# 两个 server：一个管场地，一个管日历
#
# 真实场景里这是两个独立进程，甚至两个团队维护。
# ══════════════════════════════════════════════════════════════════

class VenueServer:
    """场地服务。"""

    name = "venue-server"

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": "search_venues",
                "description": "按城市和人数搜场地。已知场地编码时直接调 get_availability。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "如 '上海'"},
                        "min_capacity": {"type": "integer"},
                    },
                    "required": ["city", "min_capacity"],
                },
            },
            {
                "name": "get_availability",
                "description": "查某场地某天有没有空。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "venue_id": {"type": "string"},
                        "date": {"type": "string", "description": "YYYY-MM-DD"},
                    },
                    "required": ["venue_id", "date"],
                },
            },
        ]

    def call_tool(self, name: str, args: dict) -> str:
        if name == "search_venues":
            return json.dumps([
                {"venue_id": "V01", "capacity": 60},
                {"venue_id": "V03", "capacity": 55},
            ], ensure_ascii=False)
        if name == "get_availability":
            return json.dumps({"venue_id": args["venue_id"], "status": "AVAILABLE"})
        raise ValueError(f"未知工具: {name}")


class CalendarServer:
    """日历服务——另一个团队维护的。"""

    name = "calendar-server"

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": "check_conflict",
                "description": "查某个时间段有没有日程冲突。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "start_time": {"type": "string"},
                        "hours": {"type": "integer"},
                    },
                    "required": ["date", "start_time", "hours"],
                },
            }
        ]

    def call_tool(self, name: str, args: dict) -> str:
        if name == "check_conflict":
            return json.dumps({"conflict": False, "date": args["date"]})
        raise ValueError(f"未知工具: {name}")


# ══════════════════════════════════════════════════════════════════
# client：一个 client 对一个 server
#
# 注意它不知道 server 内部怎么实现——只知道协议。
# ══════════════════════════════════════════════════════════════════

class Client:
    def __init__(self, server):
        self.server = server

    def handshake(self) -> dict:
        """初始化握手。真实 MCP 里会交换版本和 capabilities。"""
        return {"server": self.server.name, "protocol": "2025-06-18"}

    def list_tools(self) -> list[dict]:
        return self.server.list_tools()

    def call_tool(self, name: str, args: dict) -> str:
        return self.server.call_tool(name, args)


def main() -> None:
    # ── Host 同时连两个 server ──────────────────────────────
    clients = [Client(VenueServer()), Client(CalendarServer())]

    print("=" * 64)
    print("① 握手")
    print("=" * 64)
    for c in clients:
        h = c.handshake()
        print(f"  连上 {h['server']:16s} 协议版本 {h['protocol']}")

    print()
    print("=" * 64)
    print("② 汇总工具列表（这就是「模型能看到什么」）")
    print("=" * 64)
    all_tools = []
    for c in clients:
        for t in c.list_tools():
            all_tools.append((c, t))
            print(f"  [{c.server.name:16s}] {t['name']}")

    print(f"\n  共 {len(all_tools)} 个工具，来自 {len(clients)} 个 server")

    print()
    print("=" * 64)
    print("③ 模型选了 search_venues，client 去调")
    print("=" * 64)
    target = next((c, t) for c, t in all_tools if t["name"] == "search_venues")
    c, t = target
    print(f"  参数 schema：{json.dumps(t['inputSchema']['properties'], ensure_ascii=False)}")
    result = c.call_tool("search_venues", {"city": "上海", "min_capacity": 50})
    print(f"  返回：{result}")

    print()
    print("=" * 64)
    print("④ 模型又选了 check_conflict，换个 client")
    print("=" * 64)
    c2 = next(c for c, _ in all_tools if c.server.name == "calendar-server")
    result2 = c2.call_tool("check_conflict",
                           {"date": "2026-11-06", "start_time": "09:00", "hours": 4})
    print(f"  返回：{result2}")

    print()
    print("=" * 64)
    print("MCP 到底解决了什么")
    print("=" * 64)
    print("""
  没有 MCP：
    每个 agent 都要为每个 server 写一遍适配代码
    3 个 agent × 5 个 server = 15 份

  有 MCP：
    每个 server 按协议暴露一次，每个 agent 按协议连一次
    5 + 3 = 8 份

  ─────────────────────────────────────────

  但注意：**协议只统一了"怎么问"，没统一"问什么"**。

  search_venues 和 check_conflict 的参数完全不同，
  模型还是要自己判断"该用哪个、传什么"。

  所以 MCP 不解决：
    · 选错工具
    · 参数传错
    · 多步怎么组织（那是编排层）

  它只解决：**工具从哪来、怎么发现、怎么调**。
""")

    print("=" * 64)
    print("一个容易误解的点")
    print("=" * 64)
    print("""
  有人以为"接了 MCP，agent 就能用生态里所有工具了"。

  不会。工具列表是要**显式挂载**的。

  你能用哪些 server，取决于：
    · 你在 client 里配了哪几个
    · 每个 server 允许你调哪些工具

  ─────────────────────────────────────────

  还有个现实问题：**工具一多就退化**。

  第 03 章讲过：超过 ~30 个工具开始选错。
  接 10 个 server、每个 5 个工具 = 50 个，肯定退化。

  所以真接了 MCP，还要做**分层**：
    · 按任务阶段只挂载相关的几个
    · 或者用子 agent 隔离
""")


if __name__ == "__main__":
    main()

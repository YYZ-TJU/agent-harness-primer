"""例 2：让模型用工具。

跑法：
    python examples/ch1_langchain/e02_tool.py

这是整个 agent 最核心的一件事，只有三步：

    ① 问模型          → 它说"我要用某个工具，参数是这些"
    ② 你去执行        → 拿到结果，塞回对话
    ③ 再问模型        → 它看到结果，给结论

就这三步。后面所有复杂系统，都是在这三步外面加东西。

如果只记住一件事：

    模型只会"说"，不会"做"。
    它说"我要查场地"，场地并不会真的被查——
    真正查的是你写的代码，查完把结果告诉它。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from examples.ch1_langchain.fake_llm import FakeLLM


# ══════════════════════════════════════════════════════════════════
# 第一步：写一个真能干活的函数
#
# 这就是所谓的「工具」。没别的，就是一个普通 Python 函数。
#
# 注意它返回的是 JSON 字符串，不是 Python 对象。
# 为什么：因为结果最终要变成文字塞给模型，模型只看得懂文字。
# ══════════════════════════════════════════════════════════════════

def search_venues(city: str, min_capacity: int) -> str:
    """按城市和人数搜场地。

    真实系统里这里会去查数据库。
    为了教学，直接返回写死的数据。
    """
    fake_db = [
        {"venue_id": "V01", "name": "国家会展中心·会议室A", "capacity": 60},
        {"venue_id": "V02", "name": "洲际酒店·多功能厅", "capacity": 80},
        {"venue_id": "V03", "name": "虹桥宾馆·小会议室", "capacity": 30},
    ]
    hit = [v for v in fake_db if v["capacity"] >= min_capacity]
    return json.dumps(hit, ensure_ascii=False)


def main() -> None:
    llm = FakeLLM(verbose=True)

    # 对话记录。注意它是个列表，我们会往里面不断追加。
    messages = [
        SystemMessage(content="你是会务助手。"),
        HumanMessage(content="订个 50 人的场地。"),
    ]

    print("=" * 62)
    print("① 问模型")
    print("=" * 62)
    reply = llm.invoke(messages)

    # 把模型这句话也记进对话。**这一步不能漏**，原因见下面的坑。
    messages.append(reply)

    print(f"  模型说：{reply.content}")
    print(f"  它想调用：{[c['name'] for c in reply.tool_calls]}")

    # ── 如果没有工具调用，流程就结束了 ────────────────────
    if not reply.tool_calls:
        print("  模型没要求调工具，直接给答复。流程结束。")
        return

    # ══════════════════════════════════════════════════════
    # ② 你去执行
    #
    # 模型给了"点菜单"，现在后厨要真的做菜。
    # ══════════════════════════════════════════════════════
    print()
    print("=" * 62)
    print("② 执行工具")
    print("=" * 62)

    # 工具名 → 函数。这样模型说"我要用 search_venues"，我们就能找到对应函数。
    tool_map = {"search_venues": search_venues}

    for call in reply.tool_calls:
        name = call["name"]        # 要哪个工具
        args = call["args"]        # 参数是什么
        call_id = call["id"]       # 取餐号

        print(f"  要执行：{name}")
        print(f"  参数：  {args}")
        print(f"  取餐号：{call_id}")

        # 真的执行
        result = tool_map[name](**args)
        print(f"  结果：  {result[:70]}…")

        # ══════════════════════════════════════════════════
        # 把结果塞回对话。
        #
        # 这里必须用 ToolMessage，而且是**工具返回的**，不是模型说的。
        # tool_call_id 一定要对上刚才那个取餐号——
        # 对不上，模型就不知道这个结果是回应它哪个请求的。
        # ══════════════════════════════════════════════════
        messages.append(ToolMessage(
            content=result,
            tool_call_id=call_id,
            name=name,
        ))

    # ══════════════════════════════════════════════════════
    # ③ 再问模型
    #
    # 现在对话是：
    #   用户：订个 50 人的场地
    #   模型：我要查场地（取餐号 call_1）
    #   工具：查到了，[V01, V02]（取餐号 call_1）
    #
    # 模型看到这个，就知道"我查过了，可以下结论了"。
    # ══════════════════════════════════════════════════════
    print()
    print("=" * 62)
    print("③ 把结果告诉模型，再问一次")
    print("=" * 62)
    final = llm.invoke(messages)

    print(f"  模型最终答复：{final.content}")
    print()
    print(f"  对话里现在有 {len(messages)} 条消息：")
    for i, m in enumerate(messages):
        preview = str(m.content)[:40]
        print(f"    {i}. {type(m).__name__:12s} {preview}")

    # ══════════════════════════════════════════════════════
    # 一个必踩的坑
    # ══════════════════════════════════════════════════════
    print()
    print("=" * 62)
    print("常见错误：忘了把模型的回复也 append 进 messages")
    print("=" * 62)

    bad_messages = [
        SystemMessage(content="你是会务助手。"),
        HumanMessage(content="订个 50 人的场地。"),
        # 注意：这里缺了 AIMessage（模型的"我要查场地"那句话）
        ToolMessage(content='[{"venue_id": "V01"}]',
                    tool_call_id="call_1", name="search_venues"),
    ]
    print("  如果不 append 模型那句「我要查场地」，对话就变成：")
    for m in bad_messages:
        print(f"    {type(m).__name__:12s} {str(m.content)[:40]}")
    print()
    print("  模型会看到一个莫名其妙的结果——它不知道自己什么时候要过东西。")
    print("  真实模型在这种情况下，往往会：重复调工具、或者干脆忽略结果。")


if __name__ == "__main__":
    main()

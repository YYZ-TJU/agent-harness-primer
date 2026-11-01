"""例 3：多轮对话——模型其实没有记忆。

跑法：
    python examples/ch1_langchain/e03_multi_turn.py

如果只记住一件事：

    模型是无状态的。
    它不记得你上一次说了什么。

    每次调用，你都要把**全部历史**重新传一遍。
    这和你熟悉的「DataFrame 增量更新」完全不同，
    更像是每次调用都重新传整个 DataFrame。

这一点最容易误解，因为你在网页版 ChatGPT 里聊得很顺，
会以为模型"记得"。其实不记得——是网页每次都把历史重发了。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from examples.ch1_langchain.fake_llm import FakeLLM


class MemoryFakeLLM:
    """一个会"看历史"的假模型，用来演示有/无历史的区别。

    规则：如果对话里提到过 V02，就回答 V02 的事；否则就不知道。
    """

    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        # 把全部消息拼成一段文字，看里面有没有 V02
        all_text = " ".join(str(m.content) for m in messages)
        last = str(messages[-1].content)

        if "V02" not in all_text:
            return AIMessage(content="我没看到 V02 的信息，能补充一下吗？")
        if "V02" in last and "V02" not in " ".join(str(m.content) for m in messages[:-1]):
            return AIMessage(content="V02 是什么？我们之前聊过吗？")
        return AIMessage(content="V02 是洲际酒店的多功能厅，容纳 80 人，之前查过。")


def main() -> None:
    llm = MemoryFakeLLM()

    print("=" * 62)
    print("场景 A：不带历史，直接问第二句")
    print("=" * 62)
    print("  真实场景里，很多人以为这样就行——")
    print("  「我刚才不是说过吗，它应该记得啊」")
    print()

    only_question = [HumanMessage(content="V02 能坐多少人？")]
    print("  发出去的消息：")
    for m in only_question:
        print(f"    {type(m).__name__:12s} {m.content}")
    reply = llm.invoke(only_question)
    print(f"  模型回答：{reply.content}")
    print()
    print("  ↑ 模型不知道 V02 是什么。因为它真的没有记忆。")

    print()
    print("=" * 62)
    print("场景 B：带上历史")
    print("=" * 62)

    history = [
        SystemMessage(content="你是会务助手。"),
        HumanMessage(content="帮我看看 V02 这个场地。"),
        AIMessage(content="V02 是洲际酒店的多功能厅，容纳 80 人。"),
        HumanMessage(content="V02 能坐多少人？"),   # ← 这一句和场景 A 一模一样
    ]
    print("  发出去的消息：")
    for m in history:
        print(f"    {type(m).__name__:12s} {str(m.content)[:44]}")
    reply2 = llm.invoke(history)
    print(f"  模型回答：{reply2.content}")
    print()
    print("  ↑ 同一句话，这次答对了。区别只在于：历史传过去了。")

    print()
    print("=" * 62)
    print("这件事的实际影响：钱")
    print("=" * 62)
    print()
    print("  既然每次都要传全部历史，那对话越长，每次花的 token 越多。")
    print()
    print("  轮次    这次传几条    累计 token（估）")
    print("  " + "-" * 44)
    total = 0
    for turn in range(1, 7):
        n_msgs = turn * 2           # 每轮一问一答
        this_time = n_msgs * 120    # 粗略：每条 120 token
        total += this_time
        print(f"  第 {turn} 轮    {n_msgs:2d} 条        {total:5d}")
    print()
    print("  ↑ 第 6 轮的时候，为了说一句「好」，你要把前面 11 条全传一遍。")
    print("  这就是「上下文管理」要解决的问题（见第三章 05）。")


if __name__ == "__main__":
    main()

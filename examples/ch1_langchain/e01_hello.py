"""例 1：最小的一次对话。

跑法：
    cd agent-harness-lab
    python examples/ch1_langchain/e01_hello.py

你会看到什么：

    你给模型两条消息，它返回一条。
    就这么简单。

如果只记住一件事：

    模型是个函数。
    输入：一串消息（列表）
    输出：一条消息

    和你写过的 model.predict(X) 没本质区别，
    只是 X 从"特征矩阵"变成了"消息列表"。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from examples.ch1_langchain.fake_llm import FakeLLM


def main() -> None:
    llm = FakeLLM(verbose=True)

    # ── 消息就是「角色 + 内容」 ──────────────────────────────
    #
    # 四种角色，对应四种说话的人：
    #
    #   SystemMessage  系统设定（"你是谁、有什么规矩"）—— 相当于给模型的 system prompt
    #   HumanMessage   用户说的话
    #   AIMessage      模型说的话
    #   ToolMessage    工具返回的结果（注意：不是模型说的）
    #
    # 这个顺序不能乱：系统设定在前，对话在后。
    messages = [
        SystemMessage(content="你是会务助手，只订上海的场地。"),
        HumanMessage(content="订个 50 人的场地，11 月 6 日。"),
    ]

    print("=" * 60)
    print("我们要发给模型的消息：")
    for m in messages:
        print(f"  {type(m).__name__:15s} {m.content}")

    # ── 调用 ────────────────────────────────────────────────
    #
    # invoke 的意思是「调用一次，等它算完，拿到结果」。
    # 对应数据分析里你熟悉的：
    #
    #     result = model.predict(X)     # 等它算完
    #
    # 不是流式（边算边出），就是一次给完。
    print("=" * 60)
    print("调用模型：")
    reply = llm.invoke(messages)

    print("=" * 60)
    print("模型返回：")
    print(f"  类型：{type(reply).__name__}")
    print(f"  内容：{reply.content}")
    print(f"  工具调用：{reply.tool_calls}")

    # ── 关键点：模型没有"行动"，它只是"说了句话" ──────────────
    #
    # 上面那个 tool_calls 是模型在说：
    #   "我想用 search_venues 这个工具，参数是 city=上海, min_capacity=50"
    #
    # 但场地并没有真的被查。
    # 模型只能"提要求"，真正的执行要你来写。
    #
    # 这就是 agent 和"聊天机器人"的分界线：
    #   聊天机器人：模型说什么，就是什么
    #   agent：模型说要做什么，你去执行，再把结果告诉它
    if reply.tool_calls:
        print()
        print("注意：模型只是「说要查」，并没有真的查。")
        print("      真正去查的代码，是下一个例子要写的。")


if __name__ == "__main__":
    main()

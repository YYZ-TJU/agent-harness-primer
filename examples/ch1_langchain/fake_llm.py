"""一个假的模型，用来教学。

为什么需要它：

    真模型要 API key、要花钱、每次结果还不一样。
    教学最怕"结果不稳定"——你改一个参数，分不清是改动生效了还是模型抽风。

    这个假模型行为完全确定：同样的输入，永远同样的输出。

它模拟的是什么：

    模型本质上是个函数——你给它一串消息，它返回一条消息。
    就这么简单。所有复杂性都在"消息怎么组织"上，不在模型本身。
"""
from __future__ import annotations

from typing import Any, List

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


class FakeLLM:
    """假模型。

    行为规则（故意写得很简单，方便你看懂）：

        最后一条是「用户消息」   → 返回一个工具调用（说要查场地）
        最后一条是「工具结果」   → 返回最终答复
        其他                     → 返回一句固定的话
    """

    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
        self.call_count = 0

    def invoke(self, messages: List[Any]) -> AIMessage:
        self.call_count += 1
        last = messages[-1]

        if self.verbose:
            print(f"  [假模型第 {self.call_count} 次被调用]")
            print(f"    它收到 {len(messages)} 条消息，最后一条是 {type(last).__name__}")

        # 情况一：用户刚说话 → 假装"我要先查一下场地"
        if isinstance(last, HumanMessage):
            return AIMessage(
                content="我先查一下上海的场地。",
                tool_calls=[{
                    "name": "search_venues",
                    "args": {"city": "上海", "min_capacity": 50},
                    "id": f"call_{self.call_count}",
                }],
            )

        # 情况二：工具结果回来了 → 假装"看完了，给结论"
        if isinstance(last, ToolMessage):
            return AIMessage(
                content=f"查到了，结果是这样的：{str(last.content)[:60]}",
            )

        # 兜底
        return AIMessage(content="（假模型不知道说什么）")

"""例 4：流式 vs 一次性。

跑法：
    python examples/ch1_langchain/e04_stream.py

如果只记住一件事：

    一次性（invoke）：等它全算完，一次给你。
    流式（stream）：  算一点给一点，你能边看边等。

类比你已经很熟的东西：

    一次性    = pd.read_csv("大文件.csv")        # 等 30 秒，然后拿到完整 DataFrame
    流式      = pd.read_csv(..., chunksize=1000)  # 每 1000 行就给你一块，可以先处理

什么时候需要流式：

    任务要跑 20 秒 → 用户盯着空屏幕会以为卡死
    用流式 → 至少能看到"我在做事"
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain_core.messages import AIMessage, HumanMessage

# 一段假装是模型生成的文字
SENTENCE = "我查了三个场地，V01 容量 60 人报价 8280，在预算内。"


# ══════════════════════════════════════════════════════════════════
# 一次性：等全部算完
# ══════════════════════════════════════════════════════════════════

def generate_all() -> AIMessage:
    """假装模型算了 2 秒，然后一次性返回全部内容。"""
    time.sleep(2)
    return AIMessage(content=SENTENCE)


# ══════════════════════════════════════════════════════════════════
# 流式：算一点给一点
#
# 注意这个函数里有 yield ——
# 意思是"先别急着算完，每算出一块就交出去一块"，
# 调用方每拿到一块就能立刻用。
#
# 你在数据分析里见过类似的：读大文件时一行一行处理，而不是全部读进内存。
# ══════════════════════════════════════════════════════════════════

def generate_stream():
    """假装模型一个词一个词往外蹦。"""
    chunk_size = 6
    for i in range(0, len(SENTENCE), chunk_size):
        time.sleep(0.25)                       # 每块算 0.25 秒
        yield SENTENCE[i:i + chunk_size]        # 交出去一块


def main() -> None:
    messages = [HumanMessage(content="预算 9000，能不能订？")]

    print("=" * 62)
    print("方式一：一次性（invoke）")
    print("=" * 62)
    print("  调用后会发生什么：屏幕空白 2 秒，然后突然出现整段话。")
    print()
    t0 = time.time()
    print("  调用中…", end="", flush=True)
    reply = generate_all()
    elapsed = time.time() - t0
    print(f"\r  耗时 {elapsed:.1f} 秒，一次性拿到：")
    print(f"    {reply.content}")

    print()
    print("=" * 62)
    print("方式二：流式（stream）")
    print("=" * 62)
    print("  调用后会发生什么：每 0.25 秒蹦出几个字，你能看到进度。")
    print()

    t0 = time.time()
    print("  输出：", end=" ", flush=True)
    pieces = []
    for chunk in generate_stream():
        pieces.append(chunk)
        # 每拿到一块就立刻打印，不换行
        print(chunk, end="", flush=True)
    elapsed = time.time() - t0
    print()
    print(f"  耗时 {elapsed:.1f} 秒，分 {len(pieces)} 次拿到")

    print()
    print("=" * 62)
    print("两者对比")
    print("=" * 62)
    print("  总耗时差不多（都是 2 秒左右）。")
    print("  但用户体验完全不同：")
    print()
    print("    一次性：2 秒内什么都看不到 → 用户以为卡死了")
    print("    流式：  每 0.25 秒有反馈   → 用户知道在跑")
    print()
    print("  这就是为什么我们的 engine 用 stream 而不是 invoke。")
    print("  不只是为了好看——第 5 章讲的「中断」，也依赖流式：")
    print("  只有边跑边出，才能在中间插入检查点。")


if __name__ == "__main__":
    main()

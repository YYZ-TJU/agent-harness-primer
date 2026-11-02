"""例 5：RAG 的检索到底在干什么——手写一个最简版。

跑法：
    python examples/ch3_concepts/e05_rag.py

不用真 embedding，用词频向量代替。
目的不是教你造轮子，是让你看清"检索"这一步在算什么。
"""
from __future__ import annotations

import math
import re
from collections import Counter


# ══════════════════════════════════════════════════════════════════
# 一、分块
#
# 真实系统里用几百字一块 + 重叠。
# 这里用一句话一块，方便看清。
# ══════════════════════════════════════════════════════════════════

DOCS = {
    "员工手册_v3": [
        "年假按工龄计算，满一年 5 天，满三年 10 天，满五年 15 天。",
        "请假需提前三个工作日申请，三天以上需要部门总监审批。",
        "加班可以调休，调休需在三个月内使用。",
    ],
    "差旅制度_v2": [
        "出差住宿标准：一线城市每晚 600 元，二线城市 450 元。",
        "交通费实报实销，高铁二等座，飞机经济舱。",
        "出差补贴每天 100 元，含餐费和市内交通。",
    ],
    "场地预订流程": [
        "订场地先查档期，确认可用后再查报价。",
        "金额超过预算 85% 需要走审批流程。",
        "下单后 24 小时内可以免费取消。",
    ],
}


def tokenize(text: str) -> list[str]:
    """粗暴分词：按双字切（2-gram）。

    为什么不用单字：单字重合度太低，"出差住宿"和"出差住宿标准"
    在单字维度上几乎一样，区分不出相关性。

    双字能抓住"出差""住宿"这类词组。
    真实系统用分词器或子词切分，但思路一样：把文本拆成可比较的单元。
    """
    chars = re.sub(r"[，。：、\s]+", "", text)
    return [chars[i:i + 2] for i in range(len(chars) - 1)]


def to_vector(text: str) -> Counter:
    """把文本变成词频向量。

    真实 embedding 是 768-3072 维的稠密向量，
    这里是稀疏的词频——但"比较相似度"的逻辑一样。
    """
    return Counter(tokenize(text))


def cosine(a: Counter, b: Counter) -> float:
    """余弦相似度：两个向量夹角的余弦。

    1 = 完全同向，0 = 无关。
    """
    common = set(a) & set(b)
    dot = sum(a[k] * b[k] for k in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def main() -> None:
    # ── 建索引（离线做一次） ──────────────────────────────
    index = []
    for doc_name, chunks in DOCS.items():
        for i, chunk in enumerate(chunks):
            index.append({
                "text": chunk,
                "source": doc_name,
                "chunk_no": i,
                "vec": to_vector(chunk),
            })

    print("=" * 64)
    print("① 建索引")
    print("=" * 64)
    print(f"  {len(DOCS)} 份文档，切成 {len(index)} 块")
    for doc_name, chunks in DOCS.items():
        print(f"    {doc_name}: {len(chunks)} 块")

    # ── 检索 ────────────────────────────────────────────
    question = "出差住宿能报多少"

    print()
    print("=" * 64)
    print(f"② 检索：{question}")
    print("=" * 64)

    q_vec = to_vector(question)
    scored = [(cosine(q_vec, item["vec"]), item) for item in index]
    scored.sort(key=lambda x: -x[0])

    for score, item in scored[:4]:
        flag = "←" if score >= 0.2 else " "
        print(f"  {score:.3f} {flag} [{item['source']}] {item['text'][:30]}")

    print()
    print("  说明：分越高越相关。0.2 以上通常是真命中。")

    # ── 增强 ────────────────────────────────────────────
    top = [item for score, item in scored[:3] if score >= 0.2]

    print()
    print("=" * 64)
    print("③ 拼成提示词")
    print("=" * 64)
    context = "\n".join(f"[{t['source']}] {t['text']}" for t in top)
    prompt = f"""基于以下资料回答问题。资料里没有的，说「不知道」。

<资料>
{context}
</资料>

问题：{question}"""
    print(prompt)

    # ── 一个关键对比 ────────────────────────────────────
    print("=" * 64)
    print("④ 关键：检索不到会怎样")
    print("=" * 64)

    bad_q = "公司股票代码是多少"
    bad_vec = to_vector(bad_q)
    bad_scored = [(cosine(bad_vec, item["vec"]), item) for item in index]
    best_score, best_item = max(bad_scored, key=lambda x: x[0])

    print(f"  问：{bad_q}")
    print(f"  最高相似度：{best_score:.3f}（[{best_item['source']}] {best_item['text'][:24]}）")
    print()
    print(f"  → {best_score:.3f} 低于阈值 0.2，说明「资料里没有」")
    print("     正确做法：告诉用户不知道，而不是硬拿最像的那条去答")

    print()
    print("=" * 64)
    print("为什么阈值很重要")
    print("=" * 64)
    print("""
  向量检索永远会返回"最像的 top-k"——哪怕全是无关的。

  如果你不设阈值：
    问"股票代码"，它会拿"交通费实报实销"去答
    因为那三条里就这条"最像"

  模型拿到这条，会硬编一个答案出来。

  ─────────────────────────────────────────

  所以 RAG 的 prompt 里必须有这句：

    资料里没有的，说「不知道」。

  而且要有阈值过滤，相似度太低的直接不进上下文。
""")

    print("=" * 64)
    print("真实系统和这个例子的差别")
    print("=" * 64)
    print("""
  这个例子                 真实系统
  ────────────────────────────────────────────
  按字切                   分词器 / 子词
  词频向量                 768-3072 维稠密向量
  余弦相似度               向量库（FAISS / Qdrant）
  3 份文档、9 块           几千到几百万块
  一次检索                 可能多路召回 + rerank

  但核心逻辑一样：
    把问题变成向量 → 找最近的几块 → 塞进提示词
""")


if __name__ == "__main__":
    main()

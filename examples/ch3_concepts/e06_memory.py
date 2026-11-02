"""例 6：记忆怎么提取、怎么冲突、怎么隔离。

跑法：
    python examples/ch3_concepts/e06_memory.py

不调模型，用规则模拟"提取"这一步。
重点不是提取算法，是**三个坑**：
    什么都记 / 冲突不处理 / 记忆污染
"""
from __future__ import annotations

import re


# ══════════════════════════════════════════════════════════════════
# 一、提取：从对话里挑出"值得长期记住的"
#
# 真实系统用模型提取，这里用规则——因为要演示的是"挑什么"，
# 不是"怎么挑"。
# ══════════════════════════════════════════════════════════════════

def extract(turn: str) -> list[dict]:
    """三条规则，对应三类值得记的东西。"""
    found = []

    # ① 事实：带明确归属的陈述
    if m := re.search(r"(我是|我们属于)(\S{2,8}(分公司|部门|团队))", turn):
        found.append({"type": "fact", "key": "org",
                      "content": m.group(2), "confidence": 0.95})

    # ② 偏好："总是/一般/习惯"后面的完整短语（到标点为止）
    if m := re.search(r"(?:总是|一般|习惯|偏好)([^，。；]{2,16})", turn):
        found.append({"type": "preference", "key": "habit",
                      "content": m.group(1).strip(), "confidence": 0.7})

    # ③ 踩过的坑：开头那个实体 + 问题描述
    if m := re.search(r"^(\S{2,4})[^，。]{0,12}(不好|别用|踩过|有问题)", turn):
        found.append({"type": "pitfall", "key": m.group(1),
                      "content": turn[:40], "confidence": 0.85})

    return found


# ══════════════════════════════════════════════════════════════════
# 二、存储：带作用域
#
# 关键设计：每条记忆都有 user_id。
# 没有它，A 的记忆会污染 B。
# ══════════════════════════════════════════════════════════════════

class MemoryStore:
    def __init__(self):
        self._data: list[dict] = []

    def write(self, user_id: str, mem: dict) -> str:
        # 冲突检测：同一用户、同一 key、内容不同
        for old in self._data:
            if (old["user_id"] == user_id
                    and old["type"] == mem["type"]
                    and old["key"] == mem["key"]
                    and old["content"] != mem["content"]):
                # 不覆盖，标记冲突
                self._data.append({**mem, "user_id": user_id,
                                   "status": "conflict",
                                   "vs": old["content"]})
                return "conflict"
        self._data.append({**mem, "user_id": user_id, "status": "ok"})
        return "ok"

    def read(self, user_id: str) -> list[dict]:
        return [m for m in self._data if m["user_id"] == user_id]

    def search(self, user_id: str, query: str, top_k: int = 3) -> list[dict]:
        """最简检索：按字重合度排。

        关键是第一个参数 user_id——**过滤在检索之前**，
        不是检索完再过滤。
        """
        pool = self.read(user_id)
        scored = []
        for m in pool:
            overlap = len(set(query) & set(m["content"]))
            scored.append((overlap, m))
        scored.sort(key=lambda x: -x[0])
        return [m for _, m in scored[:top_k]]


def main() -> None:
    store = MemoryStore()

    print("=" * 64)
    print("① 提取")
    print("=" * 64)
    turns = [
        "我是上海分公司的",
        "订场地一般都要上午 9 点开始",
        "V01 那个场地音响不好",
        "这次预算 9000",
    ]
    for t in turns:
        mems = extract(t)
        print(f"  「{t}」")
        if not mems:
            print("    → 不记（没有值得长期保留的）")
        for m in mems:
            print(f"    → [{m['type']}] {m['key']} = {m['content']} "
                  f"(置信度 {m['confidence']})")
            print(f"      写入：{store.write('u1', m)}")

    print()
    print("=" * 64)
    print("② 注意第 4 句：预算不记")
    print("=" * 64)
    print("""
  「这次预算 9000」没被提取——因为它是**这一次**的条件，
  不是**长期**的偏好。

  如果记成"用户预算上限 9000"，下次用户说要 2 万的场地，
  模型会拿记忆去反驳他。

  ─────────────────────────────────────────

  这条是"什么都记"的典型症状：
  把一次性条件当成永久偏好。

  判断标准：**下个月还成立吗？**
    不成立 → 不记
    可能变 → 记，但标低置信度
    长期成立 → 记
""")

    print("=" * 64)
    print("③ 冲突")
    print("=" * 64)
    r = store.write("u1", {"type": "fact", "key": "org",
                           "content": "北京分公司", "confidence": 0.95})
    print("  用户后来说：'我调到北京分公司了'")
    print(f"  → 写入结果：{r}")
    print()
    print("  记忆里现在有两条 org：")
    for m in store.read("u1"):
        if m["key"] == "org":
            mark = f"  ⚠️ 与「{m.get('vs')}」冲突" if m["status"] == "conflict" else ""
            print(f"    {m['content']:14s} [{m['status']}]{mark}")
    print()
    print("  → 不自动覆盖，标记冲突等确认")
    print("     自动覆盖的风险：万一是用户说错了，旧值就没了")

    print()
    print("=" * 64)
    print("④ 隔离")
    print("=" * 64)
    store.write("u2", {"type": "fact", "key": "org",
                       "content": "深圳分公司", "confidence": 0.95})
    print("  另一个用户 u2 也说了他的公司：深圳分公司")
    print()
    print("  u1 能查到什么（搜「分公司」）：")
    for m in store.search("u1", "分公司"):
        print(f"    {m['content']}")
    print()
    print("  u2 能查到什么：")
    for m in store.search("u2", "分公司"):
        print(f"    {m['content']}")
    print()
    print("  → 各查各的。")
    print("    如果 search 没带 user_id，u1 会看到「深圳分公司」——")
    print("    这就是记忆污染，和第 17 章讲的并发隔离是同一个错误。")

    print()
    print("=" * 64)
    print("三个坑对照")
    print("=" * 64)
    print("""
  坑            症状                    修法
  ────────────────────────────────────────────────────────
  什么都记       检索越来越不准          只记三类 + 置信度阈值
  冲突不处理     用户改了口，记忆还是旧的  不覆盖，标冲突
  记忆污染      A 的记忆影响 B          user_id 过滤在检索之前

  ─────────────────────────────────────────

  三个坑的共同点：**不报错**。

  记忆写进去了、检索也有结果，但答案是错的。
  和评估那个坑一样——最难发现的是"看起来在工作"。
""")


if __name__ == "__main__":
    main()

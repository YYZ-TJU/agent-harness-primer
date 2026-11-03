"""文档自检：链接、编号、结构。

本地跑：
    python scripts/check_docs.py

CI 里跑：见 .github/workflows/ci.yml

为什么需要它：
    章节目录改过两次编号，每次都有链接漏改。
    肉眼看不出 20 多个文件里哪一条错了。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "guide"

errors: list[str] = []


def check_links() -> None:
    """所有 .md 里的相对链接必须存在。

    跳过代码块——里面有故意写的错误示例。
    """
    for f in ROOT.rglob("*.md"):
        text = f.read_text(encoding="utf-8")
        # 去掉代码块和行内代码
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        text = re.sub(r"`[^`]*`", "", text)

        for m in re.finditer(r"\]\(([^)#]+\.md)\)", text):
            target = m.group(1)
            if not (f.parent / target).resolve().exists():
                errors.append(f"[链接] {f.relative_to(ROOT)} → {target}")


def check_numbering() -> None:
    """guide/ 下的章节编号必须从 01 连续。"""
    files = sorted(GUIDE.glob("*.md"))
    if not files:
        errors.append("[编号] guide/ 下没有章节")
        return

    nums = []
    for f in files:
        m = re.match(r"^(\d{2})-", f.name)
        if not m:
            errors.append(f"[编号] {f.name} 不符合 NN-标题.md 格式")
            continue
        nums.append(int(m.group(1)))

    expected = list(range(1, len(nums) + 1))
    if nums != expected:
        errors.append(f"[编号] 不连续：期望 {expected}，实际 {nums}")


def check_section_numbers() -> None:
    """每章的二级标题编号必须递增且不重复。

    为什么需要：插入新小节时改了标题忘了改编号，
    会出现两个「六、」。肉眼很难发现。
    """
    cn = "一二三四五六七八九十"
    for f in sorted(GUIDE.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        # 只取二级标题（## 一、xxx），跳过代码块
        body = re.sub(r"```.*?```", "", text, flags=re.S)
        found = re.findall(r"^## ([一二三四五六七八九十]+)、", body, re.M)
        if not found:
            continue

        # 中文数字转 int
        def cn2int(c: str) -> int:
            if c == "十":
                return 10
            if c.startswith("十"):
                return 10 + cn.index(c[1]) + 1
            if c.endswith("十"):
                return (cn.index(c[0]) + 1) * 10
            if len(c) == 1:
                return cn.index(c) + 1
            return 0

        nums = [cn2int(c) for c in found]
        expected = list(range(1, len(nums) + 1))
        if nums != expected:
            errors.append(
                f"[小节] {f.name} 编号不连续：{found}（应为 一到{found[-1] if found else ''}）")


def check_h1() -> None:
    """每章第一行必须是 # NN · 标题，且编号和文件名一致。"""
    for f in sorted(GUIDE.glob("*.md")):
        first = f.read_text(encoding="utf-8").splitlines()[0]
        m = re.match(r"^# (\d{2}) · ", first)
        if not m:
            errors.append(f"[标题] {f.name} 第一行格式不对：{first[:40]}")
            continue
        file_num = f.name[:2]
        if m.group(1) != file_num:
            errors.append(f"[标题] {f.name} 标题编号 {m.group(1)} ≠ 文件名 {file_num}")


def check_next_links() -> None:
    """每章的「下一篇」必须指向下一章（最后一章除外）。"""
    files = sorted(GUIDE.glob("*.md"))
    for i, f in enumerate(files[:-1]):
        text = f.read_text(encoding="utf-8")
        m = re.search(r"\*\*下一篇\*\*：\[[^\]]+\]\(([^)]+)\)", text)
        if not m:
            errors.append(f"[跳转] {f.name} 缺少「下一篇」")
            continue
        expected = files[i + 1].name
        if m.group(1) != expected:
            errors.append(f"[跳转] {f.name} 下一篇指向 {m.group(1)}，应为 {expected}")


def check_required_files() -> None:
    """仓库必需文件。"""
    required = [
        "README.md", "LICENSE", "requirements.txt", "PUBLISH.md",
        "appendix/A-名词表.md", "appendix/B-数据来源.md",
        "case-study/README.md", "examples/README.md",
    ]
    for rel in required:
        if not (ROOT / rel).exists():
            errors.append(f"[文件] 缺 {rel}")


def check_examples_listed() -> None:
    """examples/README.md 里列出的例子，文件必须存在；反之亦然。"""
    readme = (ROOT / "examples" / "README.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"`(e\d{2}_[a-z_]+\.py)`", readme))

    actual = set()
    for d in ("ch1_langchain", "ch2_langgraph", "ch3_concepts"):
        for f in (ROOT / "examples" / d).glob("e*.py"):
            actual.add(f.name)

    for name in listed - actual:
        errors.append(f"[示例] README 提到 {name}，但文件不存在")
    for name in actual - listed:
        errors.append(f"[示例] 文件 {name} 存在，但 README 没列出")


def main() -> int:
    check_links()
    check_numbering()
    check_h1()
    check_section_numbers()
    check_next_links()
    check_required_files()
    check_examples_listed()

    chapters = len(list(GUIDE.glob("*.md")))
    if errors:
        print(f"发现 {len(errors)} 个问题：\n")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"全部通过（{chapters} 章）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

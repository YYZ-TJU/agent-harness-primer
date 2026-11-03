"""把 guide/ 下的 23 章合成一个单文件 HTML。

用途：
    生成可以上传到资料库（workbuddy.link）的单页版本。
    一个文件、无外部依赖、左侧目录用锚点跳转。

跑法：
    pip install markdown
    python scripts/build_single.py

输出：
    dist/library.html
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    print("需要 markdown 库：pip install markdown")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "guide"
OUT_DIR = ROOT / "dist"

# 章节分组（用于侧边栏）
GROUPS = [
    ("第一部分：背景", ["01", "02"]),
    ("第二部分：核心机制", ["03", "04", "05", "06", "07"]),
    ("第三部分：知识从哪来", ["08", "09", "10", "11"]),
    ("第四部分：多主体", ["12", "13"]),
    ("第五部分：评估", ["14", "15", "16", "17"]),
    ("第六部分：生产化", ["18", "19", "20", "21"]),
    ("第七部分：动手", ["22"]),
    ("第八部分：经验", ["23", "24"]),
]

CSS = """
:root{
  --bg:#0b0e12; --panel:#12161c; --panel2:#161b23; --border:#202834;
  --text:#d9dfe7; --muted:#8b95a4; --dim:#6b7583;
  --accent:#4cc9b0; --accent2:#5aa9e6;
  --code-bg:#0d1117; --inline:#1a212b;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0; background:var(--bg); color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  font-size:15.5px; line-height:1.85; -webkit-font-smoothing:antialiased;
}
code,pre{font-family:"SF Mono",Consolas,"Cascadia Code","JetBrains Mono",Menlo,monospace}
a{color:var(--accent2); text-decoration:none}
a:hover{text-decoration:underline}

#toc{
  position:fixed; left:0; top:0; width:280px; height:100vh; overflow-y:auto;
  padding:26px 16px 60px 22px; border-right:1px solid var(--border);
  background:var(--panel); font-size:13px;
}
#toc .brand{font-size:12px; letter-spacing:.14em; color:var(--dim); text-transform:uppercase}
#toc .brand2{font-size:15px; font-weight:650; margin:4px 0 18px}
#toc .grp{color:var(--accent); font-size:12px; font-weight:650; margin:18px 0 6px}
#toc a{display:block; padding:4px 6px; color:var(--muted); border-radius:3px; font-size:12.8px}
#toc a:hover{background:var(--panel2); color:var(--text); text-decoration:none}

main{margin-left:280px; max-width:860px; padding:30px 34px 120px}
section{margin-bottom:70px; padding-top:20px; border-top:1px solid var(--border)}
section:first-of-type{border-top:none}
h1{font-size:26px; font-weight:680; line-height:1.35; margin:6px 0 20px}
h2{font-size:20px; font-weight:650; margin:40px 0 13px; padding-top:16px; border-top:1px solid var(--border)}
h3{font-size:16.5px; font-weight:640; margin:28px 0 10px}
h4{font-size:15px; font-weight:640; margin:20px 0 8px; color:var(--accent)}
p{margin:12px 0}
ul,ol{margin:12px 0; padding-left:26px}
li{margin:6px 0}
li::marker{color:var(--dim)}
strong{color:#eef2f7; font-weight:640}
blockquote{
  margin:16px 0; padding:12px 18px; border-left:2px solid var(--accent);
  background:var(--panel); color:var(--muted);
}
blockquote p{margin:6px 0}
code{background:var(--inline); padding:1.5px 5px; border-radius:3px; font-size:.9em; color:#c9d6e4}
pre{background:var(--code-bg); border:1px solid var(--border); border-radius:5px;
  padding:14px 16px; overflow-x:auto; margin:16px 0; line-height:1.7}
pre code{background:none; padding:0; font-size:13.2px; color:#c9d6e4}
table{border-collapse:collapse; width:100%; margin:16px 0; font-size:14px}
th,td{border:1px solid var(--border); padding:8px 12px; text-align:left; vertical-align:top}
th{background:var(--panel2); color:var(--muted); font-weight:600; font-size:13px}
hr{border:none; border-top:1px solid var(--border); margin:32px 0}
.back{display:inline-block; font-size:12px; color:var(--dim); margin-bottom:14px}

@media (max-width:1100px){
  #toc{display:none}
  main{margin-left:0; max-width:100%; padding:20px 20px 100px}
}
"""


def md_to_html(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    # 去掉一级标题（章节名由外面加）
    text = re.sub(r"\A#\s+.*?\n+", "", text)
    # 站内链接转锚点
    text = re.sub(r"\]\((\d{2}-[^)]+)\.md\)", lambda m: f'](#{m.group(1)})', text)
    return markdown.markdown(text, extensions=["fenced_code", "tables", "sane_lists"])


def main() -> None:
    files = sorted(GUIDE.glob("*.md"))
    if len(files) != 24:
        print(f"警告：预期 24 章，实际 {len(files)} 章", file=sys.stderr)

    by_num = {f.name[:2]: f for f in files}

    toc_parts: list[str] = []
    body_parts: list[str] = []

    for group_name, nums in GROUPS:
        toc_parts.append(f'<div class="grp">{group_name}</div>')
        for num in nums:
            f = by_num.get(num)
            if not f:
                continue
            title = f.stem[3:]                       # 去掉 "NN-"
            anchor = f.stem
            toc_parts.append(f'<a href="#{anchor}">{num} {title}</a>')
            body_parts.append(
                f'<section id="{anchor}">'
                f'<a class="back" href="#top">↑ 回到顶部</a>'
                f'<h1>{num} · {title}</h1>'
                f'{md_to_html(f)}'
                f'</section>'
            )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Harness Primer · 24 章</title>
<style>{CSS}</style>
</head>
<body id="top">
<nav id="toc">
  <div class="brand">Primer</div>
  <div class="brand2">给数据科学背景的 Agent 入门</div>
  {''.join(toc_parts)}
</nav>
<main>
{''.join(body_parts)}
</main>
</body>
</html>
"""

    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / "library.html"
    out.write_text(html, encoding="utf-8")

    print(f"生成 {out.relative_to(ROOT)}：{len(html) / 1024:.0f} KB，{len(files)} 章")


if __name__ == "__main__":
    main()

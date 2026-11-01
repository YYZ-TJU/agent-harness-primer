# 发布说明

> 仓库怎么组织、为什么要这样组织、怎么推上去。

---

## 一、仓库结构

```
agent-harness-primer/
├── README.md                    ← 门面：讲什么、给谁看、三条学习路线
├── LICENSE                      ← MIT
├── requirements.txt             ← 只两个依赖：langchain-core、langgraph
├── .gitignore
│
├── guide/                       ← 正文，10 章
│   ├── 01-什么是agent.md
│   ├── 02-模型调用.md
│   ├── 03-工具调用.md
│   ├── 04-循环.md
│   ├── 05-状态与图.md
│   ├── 06-上下文管理.md
│   ├── 07-暂停与恢复.md
│   ├── 08-评估.md
│   ├── 09-生产化.md
│   └── 10-从零搭一个.md
│
├── examples/                    ← 9 个可跑例子
│   ├── README.md                ← 每个例子教什么 + 怎么改
│   ├── ch1_langchain/
│   │   ├── fake_llm.py          ← 假模型（不需要 key）
│   │   ├── e01_hello.py
│   │   ├── e02_tool.py
│   │   ├── e03_multi_turn.py
│   │   └── e04_stream.py
│   └── ch2_langgraph/
│       ├── e01_graph.py
│       ├── e02_reducer.py
│       ├── e03_branch.py
│       ├── e04_loop.py
│       └── e05_pause.py
│
├── case-study/                  ← 完整案例
│   └── README.md                ← 五节点图、四个工位、踩过的坑
│
└── appendix/                    ← 附录
    ├── A-名词表.md              ← 34 个词，带比喻
    └── B-数据来源.md            ← 论文、基准、可信度分级
```

**31 个文件，Markdown 6.2 万字符，Python 3.1 万字符。**

---

## 二、为什么这样组织

### 为什么 guide 分 10 章而不是 5 章

内容量决定的，不是凑数。

- **01-02** 背景：不讲代码，先分清 agent / chatbot / workflow
- **03-05** 核心：工具、循环、状态——这三样是 agent 的全部结构
- **06-07** 工程：上下文、暂停——能跑之后马上会遇到的
- **08-10** 验证：评估、生产、收口

**每章 2700-5400 字符**，一次坐得住。

### 为什么 examples 按章分目录

因为**读到哪里就能跑对应例子**。

如果想按"难度递增"排（e01 → e09 全局编号），读者会不知道哪个对应哪章。

**目录名带章节号，路径即索引。**

### 为什么 case-study 只有 README

完整实现有 50+ 文件。放进来会让仓库变成"一个项目 + 一堆文档"，而不是"一份读本"。

**案例只需要讲清设计和踩过的坑**，代码不是重点。

### 为什么用中文文件名

用户是中文读者，文件在编辑器侧边栏里要能一眼认出来。

**代价**：URL 里是百分号编码。GitHub 能正常渲染，但复制链接会很难看。

**如果你要改成英文文件名**，改完记得更新 README 和正文里的相对链接。

---

## 三、本地状态

已经 `git init` 并提交：

```
bd53c8b 初版：面向数据科学背景的 agent 入门读本
31 files changed
```

---

## 四、推送步骤

### 方案 A：先手动建仓库（推荐）

**为什么**：GitHub 连接的授权范围不含"创建仓库"，直接创建会被拒（403）。

**步骤**：

1. 打开 https://github.com/new
2. 仓库名填 `agent-harness-primer`
3. **不要**勾选 "Add a README file"（本地已有）
4. 创建

然后在这个目录执行：

```bash
cd agent-harness-primer

git remote add origin https://github.com/YYZ-TJU/agent-harness-primer.git
git branch -M main
git push -u origin main
```

**如果提示要凭据**：用 Personal Access Token 当密码（GitHub 已不支持账号密码）。

### 方案 B：重新授权 GitHub 连接

如果想让后续操作都能自动做（建仓库、推代码、改 PR），需要更宽的授权范围。

在连接器管理里重新授权 GitHub，勾选 `repo` 全权限。

**注意**：这只是可能解决——GitHub App 的权限由应用本身决定，不是所有 scope 都能通过重授权获得。

---

## 五、后续更新流程

改完内容后：

```bash
cd agent-harness-primer
git add -A
git commit -m "更新：xxx"
git push
```

### 如果要同步到线上可读版本

这个仓库是 Markdown，GitHub 直接能看。

**但如果想要"一个链接、排版好看、能发给人"**，那套在 WorkBuddy 资料库里：

- 单文件版：https://workbuddy.link/p/e506alx3SxsftcMoY9daGP
- 源文件在 `agent-harness-lab/docs/lessons/`

**两套内容同源，但组织方式不同**：

| | GitHub 仓库 | 资料库页面 |
|---|---|---|
| 面向 | 开发者、要 clone 的人 | 只想读的人 |
| 结构 | 10 章 + 例子 + 附录 | 五章（按技术栈分层） |
| 更新 | git push | 走同步流程 |

**如果只维护一套**，建议以 GitHub 为准——它能带代码。

---

## 六、几个可以改进的地方

| 项 | 现在 | 可以怎么做 |
|---|---|---|
| 英文版 | 无 | 翻译，或至少给关键术语加英文 |
| CI | 无 | 加 GitHub Actions 跑 examples，确保不会因为依赖升级而挂 |
| 图表 | 全用 ASCII | 换成 mermaid，GitHub 原生渲染 |
| 练习答案 | 散在正文 | 单独一节 |
| 版本标签 | 无 | 每章稳定后打 tag |

**最该先做的是 CI**——现在例子能跑是因为本地环境，别人 clone 下来装最新版 langgraph 可能就挂。

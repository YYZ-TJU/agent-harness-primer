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
    ├── A-名词表.md              ← 42 个词，带比喻
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

## 四、推送过程（已完成）

### 最终状态（2026-11-02）

| 项 | 状态 |
|---|---|
| 仓库 | ✅ https://github.com/YYZ-TJU/agent-harness-primer |
| 推送 | ✅ 成功，本地与远端都是 `2445e2c` |
| 文件 | 32 个 |
| 分支 | `main` |

### 试过的四条路，前三条全断

| 方式 | 报错 | 原因 |
|---|---|---|
| `git push`（HTTPS） | `could not read Username` | 没有凭据 |
| GitHub 连接器 API | `403 Resource not accessible by integration` | 应用只有读权限 |
| 重连后 API 推文件 | `unauthorized: token authentication failed` | 同上 |
| **SSH** | 先 `Permission denied`，加公钥后通了 | 公钥没注册 |

### 关键教训

**一、连接器"已连接"不等于"有写权限"**

`list_installed_plugins` 显示 `status: connected`，能查仓库、能读文件，但写操作一律 403。

**重授权也解决不了**——那是 GitHub App 本身的权限，不是 OAuth scope。

**二、SSH 是最省事的方案**

一次配好，以后所有 push 都不用再折腾：

```bash
# 1. 看公钥
cat ~/.ssh/id_rsa.pub

# 2. 加到 https://github.com/settings/keys

# 3. 改 remote 为 SSH
git remote set-url origin git@github.com:YYZ-TJU/agent-harness-primer.git

# 4. 推
git push -u origin main
```

**三、不要用 `git ls-remote` 验证**

它会读私钥，容易被安全策略拦。用 `git rev-parse origin/main` 对比本地 commit 就够了。

### 一个副作用

配好 SSH 之后，沙箱对 `~/.ssh/` 的读取会更谨慎。推送本身没问题（属于预期用途），但组合命令（比如 `ls-remote` + 其他输出）容易被拒。

**建议**：一次只做一件事，别在一条命令里混验证和操作。

---

## 五、后续更新流程

改完内容后：

```bash
cd agent-harness-primer
git add -A
git commit -m "更新：xxx"
git push          # SSH 已配好，不需要再输密码
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

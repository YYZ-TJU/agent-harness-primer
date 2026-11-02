# 08 · MCP

> 前七章讲的工具，都是你写在代码里的函数。
>
> 但如果你想让 agent 用别人写好的工具呢？这就是 MCP 要解决的问题。

---

## 一、先说它解决什么

### 一个具体的麻烦

假设你有 3 个 agent（客服、运维、数据分析），5 个数据源（GitHub、数据库、内部 API、文件系统、日历）。

**没有 MCP**：每个 agent 都要为每个数据源写一遍适配代码。

```
3 个 agent × 5 个数据源 = 15 份适配代码
```

**有 MCP**：每个数据源写一个 server，每个 agent 写一个 client。

```
5 个 server + 3 个 client = 8 份代码
```

**这就是协议的价值：把 M×N 变成 M+N。**

### 一句话定义

> **MCP（Model Context Protocol）是一个让"工具提供方"和"agent 使用方"解耦的协议。**

工具方按协议暴露能力，agent 方按协议调用。谁都不用知道对方内部怎么实现。

**类比**：USB。

- 没有 USB：每个设备一种接口（打印机并口、鼠标串口、键盘 PS/2）
- 有 USB：设备统一成 USB 口，电脑只要有一个 USB 就行

MCP 就是 agent 世界的 USB。

---

## 二、三个原语

MCP server 能暴露三种东西：

| 原语 | 是什么 | 谁决定用 | 例子 |
|---|---|---|---|
| **Tools** | 可执行的函数 | **模型**决定调用 | `create_issue`, `query_db` |
| **Resources** | 可读的数据 | **应用**决定加载 | 文件内容、数据库 schema |
| **Prompts** | 预设的提示模板 | **用户**选择 | "代码审查"模板 |

### 三者的区别

**Tools**：模型主动调。

```json
{
  "name": "search_issues",
  "description": "在仓库里搜 issue",
  "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}}
}
```

**Resources**：应用主动读，模型不一定知道。

```
file:///project/README.md
db://schema/users
```

**为什么分开**：Resource 是"背景资料"，不需要模型决定"要不要读"——应用知道该给它看什么。

**Prompts**：人选的模板。

```
/code-review  →  一段预设的审查提示词
```

**为什么分开**：这类东西不该让模型自己决定"用哪个模板"，应该由人触发。

### 一个容易混的点

**我们的 5 个工具不是 MCP。**

它们就是普通的 Python 函数，用 `@tool` 装饰器包了一下。

**区别在"能不能被别人用"**：

| | 普通工具 | MCP 工具 |
|---|---|---|
| 定义在哪 | 你的代码里 | 独立的 server |
| 谁能用 | 只有这个项目 | 任何支持 MCP 的客户端 |
| 换框架要改吗 | 要 | 不用 |

---

## 三、架构：Host / Client / Server

```
┌─────────────────────────────┐
│  Host（你的应用）            │
│  ┌───────────┐  ┌─────────┐ │
│  │ Client A  │  │ Client B│ │
│  └─────┬─────┘  └────┬────┘ │
└────────┼─────────────┼──────┘
         │             │
    ┌────▼────┐   ┌────▼────┐
    │ Server 1│   │ Server 2│
    │(GitHub) │   │ (数据库) │
    └─────────┘   └─────────┘
```

| 角色 | 干什么 |
|---|---|
| **Host** | 你的 agent 应用（管模型、管会话） |
| **Client** | 连一个 server 的连接器（一个 client 对一个 server） |
| **Server** | 暴露工具/资源/prompts 的独立进程 |

**为什么要分 Client 和 Server**：因为一个 Host 可能同时连多个 server。

比如你的 agent 同时要用 GitHub 和数据库，就有两个 client、两个 server。

### 两种传输方式

| 方式 | 用在哪 | 怎么通信 |
|---|---|---|
| **stdio** | 本地 server | 标准输入输出（父进程启动子进程） |
| **HTTP + SSE** | 远程 server | 网络请求 + 服务端推送 |

**stdio 的好处**：不用管端口、不用管认证、进程退出就断开。

**HTTP 的好处**：可以部署在远程，多个 client 共享。

---

## 四、一个最小的 server

```python
# server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

app = Server("venue-tools")

@app.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="search_venues",
            description="按城市和人数搜场地。只在需要多个候选时用；"
                        "已知场地编码时直接调 get_availability。",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 '上海'"},
                    "min_capacity": {"type": "integer", "description": "最少容纳人数"},
                },
                "required": ["city", "min_capacity"],
            },
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_venues":
        result = do_search(**arguments)
        return [types.TextContent(type="text", text=json.dumps(result))]
    raise ValueError(f"未知工具: {name}")

async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())
```

**注意 `description` 里那句话**：

> 只在需要多个候选时用；已知场地编码时直接调 get_availability。

**这就是第 3 章讲的「何时不该用」**——MCP 的工具描述和普通工具一样，都要写这个。

### 客户端怎么连

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

params = StdioServerParameters(command="python", args=["server.py"])
async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()

        tools = await session.list_tools()
        # → [Tool(name='search_venues', ...)]

        result = await session.call_tool(
            "search_venues", {"city": "上海", "min_capacity": 50})
```

**跑出来是什么**：

```
可用工具: ['search_venues']
调用结果: [{"venue_id": "V01", "capacity": 60}, ...]
```

拿到 tools 列表后，转成模型能懂的格式，塞进 `bind_tools`。之后就和你自己写的工具一样了。

---

## 五、什么时候值得用

### 一条经验门槛

> agent 用超过 **3 个**外部工具，就该考虑。
> 1-2 个不值得引入协议成本。

**"协议成本"包括**：

- 多一个进程要管（stdio）或多一个服务要部署（HTTP）
- 调试链路变长（出了错要判断是 client 还是 server）
- 版本兼容（server 升级可能破坏 client）

### 三个明确该用的信号

| 信号 | 为什么 |
|---|---|
| **多个 agent 共用同一批工具** | 写一次 server，N 个 agent 都能用 |
| **工具方和你不是一个团队** | 协议是契约，不用互相改代码 |
| **工具要独立部署/升级** | server 独立进程，不影响 agent |

### 三个明确不该用的信号

| 信号 | 为什么 |
|---|---|
| 只有 1-2 个工具 | 直接写函数更简单 |
| 工具和业务强耦合 | 抽出去反而增加理解成本 |
| 性能敏感 | 多一层进程间通信，多几毫秒 |

---

## 六、它不解决什么

**这一节最重要**，因为很多人以为 MCP 能解决一切。

| 你以为 MCP 能 | 实际 |
|---|---|
| 组织多步流程 | ❌ 那是编排层（第 5 章） |
| 让 agent 记住历史 | ❌ 那是 checkpointer（第 7 章） |
| 控制权限 | ❌ 那是策略层（第 19 章） |
| 检索文档 | ❌ 那是 RAG（第 9 章） |
| 省钱 | ❌ 工具描述一样占 token |

**一句话**：MCP 只解决"工具怎么暴露和发现"，别的都不管。

### 一个具体的误解

有人以为"用了 MCP，agent 就能自动找到合适的工具"。

**不会。** 模型还是要在工具列表里选。

MCP 只是让工具列表**能来自不同地方**，选择逻辑没变。

---

## 七、我们为什么没用

**诚实回答**：

> 我们只有 5 个本地工具，全是一个团队写的，和业务强耦合（要读 `World` 对象）。
>
> 抽成 MCP server 的收益是"别人也能用"，但我们的场景没有"别人"。
>
> 所以只留了接口，没做实现。

**如果将来要接**：

| 场景 | 怎么做 |
|---|---|
| 接公司内部 API | 写一个 server，暴露 3-5 个工具 |
| 多个 agent 共用 | 一次投入，多次复用 |
| 第三方服务（GitHub、Slack） | 用现成的 server，不用自己写 |

---

## 八、和其他"能力来源"的关系

Agent 的能力来自四个地方，容易混：

| 来源 | 提供什么 | 什么时候用 |
|---|---|---|
| **内置工具** | 你自己写的函数 | 业务强耦合、数量少 |
| **MCP** | 别人写的工具 | 多 agent 共用、外部服务 |
| **RAG** | 文档里的知识 | 知识会变、量大 |
| **Skills** | 打包的流程/提示词 | 可复用的工作方法 |

**它们的边界**：

```
工具   →  "能做什么"
RAG    →  "知道什么"
Skills →  "怎么做"
```

**MCP 是"工具的传输方式"，不是"工具本身"。** 这个区分很关键。

---

## 小结

| 问题 | 答案 |
|---|---|
| MCP 是什么 | 让工具方和使用方解耦的协议 |
| 解决什么 | M×N 变 M+N |
| 三个原语 | Tools（模型调）/ Resources（应用读）/ Prompts（人选） |
| 架构 | Host → Client → Server |
| 传输 | stdio（本地）/ HTTP+SSE（远程） |
| 什么时候用 | 超过 3 个外部工具、多 agent 共用 |
| 不解决什么 | 编排、记忆、权限、检索 |

---

## 动手练

**1. 判断该不该用**

列出你项目里的工具，数一下：

- 超过 3 个外部工具？
- 有别的 agent 要用？

两个都是"否" → 别用 MCP。

**2. 看一个真实 server**

找 GitHub 官方的 MCP server，读它的 `list_tools`，看工具描述怎么写的。

**重点看**：有没有写"何时不该用"。

**3. 设计一个**

如果要给你的项目做一个 MCP server，暴露哪几个工具？哪些不该暴露（因为只对内有用）？

---

**下一篇**：[09 · RAG](09-RAG.md) —— 让 agent 知道文档里的东西

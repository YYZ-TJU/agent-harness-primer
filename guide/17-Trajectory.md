# 17 · Trajectory

> 前面讲评估，讲的都是"结果对不对"。
>
> 这一章讲"过程"——一次任务从头到尾发生了什么，以及为什么必须完整记下来。

---

## 一、什么是轨迹

### 一句话

> **一次任务的全部决策记录，包括模型每一步看到什么、做了什么。**

### 和普通日志的区别

| | 普通日志 | 轨迹 |
|---|---|---|
| 记什么 | "调用了工具 X" | **模型当时看到的完整输入** + 它的输出 |
| 粒度 | 事件级 | 决策级 |
| 能回放吗 | 不能 | **能** |
| 用途 | 排查报错 | 排查"为什么这么决定" |

**关键差别**：普通日志告诉你"发生了什么"，轨迹告诉你"**它为什么这么做**"。

### 一个具体对照

**普通日志**：

```
[12:03:15] tool get_quote returned 8280
[12:03:16] model decided to book V01
```

**轨迹**：

```json
{
  "step": 5,
  "kind": "model.request",
  "messages": [
    {"role": "system", "content": "你是会务助手..."},
    {"role": "user", "content": "订个 50 人的场地，预算 9000"},
    {"role": "assistant", "tool_calls": [{"name": "get_quote", "args": {...}}]},
    {"role": "tool", "content": "{\"venue_id\": \"V01\", \"total\": 8280}"}
  ],
  "tokens": 1240
}
```

**轨迹里有那段 `8280` 的原文，也有模型看到它之前的所有上下文。**

**这才是能回答"为什么"的东西。**

---

## 二、轨迹里要有四样

| 要素 | 为什么 |
|---|---|
| **完整输入** | 只记输出，没法查"它看到了什么才这么说" |
| **输出** | 模型说了什么、要调什么 |
| **时间戳** | 判断是"慢"还是"卡住" |
| **token 数** | 算成本、看上下文增长 |

### 一条完整轨迹的记录

```python
def record_step(step, kind, **data):
    rec = {
        "ts": time.time(),
        "step": step,
        "kind": kind,
        **data,
    }
    with open(f"logs/{thread_id}.jsonl", "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
```

**跑出来是什么**（`logs/t1.jsonl`）：

```jsonl
{"ts":1793424000.1,"step":1,"kind":"step.started","tokens":203}
{"ts":1793424000.2,"step":1,"kind":"model.request","messages":[...],"tokens":203}
{"ts":1793424001.5,"step":1,"kind":"model.responded","calls":["search_venues"]}
{"ts":1793424001.6,"step":1,"kind":"policy.decided","tool":"search_venues","action":"allow"}
{"ts":1793424001.8,"step":1,"kind":"tool.executed","tool":"search_venues","ok":true}
```

**为什么用 JSONL**：一行一条，可以 `tail -f` 实时看，也可以用 `grep` 过滤。

---

## 三、轨迹的三个用途

### 用途一：调试

**问题**：模型为什么选了 V01 而不是更便宜的 V03？

**没有轨迹**：只能猜。

**有轨迹**：

```python
# 找第 5 步的 model.request
rec = next(r for r in read_logs(thread_id)
           if r["step"] == 5 and r["kind"] == "model.request")

# 看它当时看到的 messages
for m in rec["messages"]:
    print(f"{m['role']:10s} {m['content'][:80]}")
```

**跑出来是什么**：

```
system     你是会务助手...
user       订个 50 人的场地，预算 9000
assistant  （要调 get_quote × 4）
tool       {"venue_id": "V01", "total": 8280}
tool       {"venue_id": "V03", "total": 6100}    ← 有 V03 的报价
tool       {"venue_id": "V05", "total": 9400}
assistant  （要调 create_booking(V01)）
```

**问题定位了**：V03 更便宜，但模型选了 V01。

**再看下一步**：可能是 V03 的档期是 FULL（工具返回里有，但模型忽略了）。

**这就是轨迹的价值：能看到"模型当时手里有什么牌"。**

### 用途二：评估

**轨迹层评估**（第 13 章讲的第二层）：

```python
def check_approval_before_write(trace):
    """写操作前必须有审批。"""
    approved = False
    for step in trace:
        if step["kind"] == "approval.granted":
            approved = True
        if step["kind"] == "tool.executed" and step["tool"] in WRITE_TOOLS:
            if not approved:
                return False, f"第 {step['step']} 步无审批就写了"
    return True, ""
```

**结果对但过程错**的情况，只有轨迹能发现。

**比如**：订单落在正确场地（结果对），但它跳过了"查报价"直接下单（过程错）——这次运气好，下次就错了。

### 用途三：回放

```python
def replay_decision(trace, step):
    """把模型当时看到的东西重新发给它，看它这次怎么选。"""
    rec = next(r for r in trace
               if r["step"] == step and r["kind"] == "model.request")
    messages = rebuild_messages(rec["messages"])
    return model.invoke(messages)
```

**用途**：

- 换了新模型，用同样的输入看它是否还做同样的决定
- 改了 prompt，对比新旧输出
- 排查"是不是模型抽风"

**重要限制**：模型有随机性，重放**不一定**得到相同结果。

所以回放的价值是"看它会不会给出明显不同的答案"，不是"必须一模一样"。

---

## 四、轨迹的三种存法

| 方式 | 优点 | 缺点 |
|---|---|---|
| **JSONL 文件** | 简单、可 grep、可 append | 难查询、难关联 |
| **数据库表** | 可查询、可关联 | 要设计 schema |
| **追踪平台** | 有 UI、能可视化 | 引入外部依赖 |

### 我们的选择：JSONL

```python
# 一行一条，append-only
{"ts":..., "step":1, "kind":"model.request", "messages":[...]}
```

**为什么够用**：

- 单机、单用户
- 排查靠 `grep` + 小脚本
- 不需要跨 thread 关联

**什么时候该换**：

| 信号 | 该换什么 |
|---|---|
| 要按条件查（"所有超预算的轨迹"） | 数据库 |
| 要看跨 thread 的调用链 | 追踪平台 |
| 多人协作排查 | 追踪平台 |

---

## 五、一个必须做对的细节

### 记输入，不只记输出

**只记输出**：

```
[step 5] model → create_booking(V01)
```

**你能回答什么**：它调了什么。

**你不能回答**：它为什么选 V01（明明有更便宜的 V03）。

**记输入**：

```
[step 5] model.request  messages=[...完整上下文...]
[step 5] model.responded  create_booking(V01)
```

**这才完整。**

### 一个反例

很多系统的日志长这样：

```
INFO  Calling LLM with 12 messages
INFO  LLM responded with tool call: create_booking
```

**"12 messages" 是个数字，不是内容。**

出了事，你只知道它看过 12 条消息，不知道是哪些。

**这就是为什么第 8 章说"评估会骗你"——你连"它看到什么"都不知道，怎么判断它对不对。**

---

## 六、轨迹和评估的关系

```
轨迹  →  评估的原料
评估  →  轨迹的消费者
```

**没有轨迹，只能评估结果。**

**有轨迹，才能评估过程。**

| 能评估什么 | 需要什么 |
|---|---|
| 订单对不对 | 结果（数据库） |
| 有没有越权 | 轨迹（工具调用序列） |
| 有没有跳过步骤 | 轨迹（步骤顺序） |
| 为什么这么决定 | 轨迹（完整输入） |

**四层里，后三个都要轨迹。**

---

## 七、成本：轨迹会变大

### 一个真实的量

我们的 10 个用例，跑一轮：

```
10 个 thread × 平均 15 步 × 每步约 2KB = 约 300KB
```

**单次可接受，但累积会大**：

| 跑的次数 | 累积大小 |
|---|---|
| 1 轮 | 300 KB |
| 100 轮 | 30 MB |
| 每天 10 轮，一个月 | 900 MB |

### 三种控制手段

| 手段 | 做法 | 代价 |
|---|---|---|
| **截断长内容** | 单条消息最多存 4000 字符 | 丢失细节 |
| **采样** | 只存 1/10 的轨迹 | 可能漏掉关键的那次 |
| **分级** | 成功的只存摘要，失败的存全量 | 要区分 |

**我们的做法**：截断 + 全存。

```python
MAX_CONTENT = 4000      # 单条消息最多 4000 字符

content = m.content[:MAX_CONTENT]
```

**为什么不全存**：工具返回最多 1200 字符，4000 够覆盖。

**为什么不用采样**：出问题的往往是少数，采样容易漏。

---

## 八、一个我们踩过的坑

**早期只记了事件，没记输入。**

```python
_emit("model.responded", step, calls=[c["name"] for c in calls])
```

**当时觉得够了**：知道调了什么工具就行。

**后来出问题**：

> 某个用例模型选错了场地。看日志只知道"它调了 create_booking(V01)"，
> 不知道它当时有没有看到 V03 的报价。

**修法**：加 `model.request` 事件，记完整输入。

```python
_emit("model.request", step, messages=dump_messages(msgs), tokens=estimate_tokens(msgs))
```

**代价**：日志体积涨了 3 倍。

**收益**：能回答"为什么"。

**这个取舍值。** 因为排查一次问题的成本，远高于多存几 MB 日志。

---

## 小结

| 问题 | 答案 |
|---|---|
| 轨迹是什么 | 一次任务的全部决策记录 |
| 和日志的区别 | 轨迹记"输入"，日志记"事件" |
| 四要素 | 完整输入、输出、时间戳、token 数 |
| 三个用途 | 调试、评估、回放 |
| 存法 | JSONL / 数据库 / 追踪平台 |
| 最关键的一条 | **记输入，不只记输出** |
| 成本控制 | 截断长内容，不采样 |

---

## 动手练

**1. 检查你的日志**

你能从日志里回答"模型当时看到了什么"吗？

不能 → 缺 `model.request`。

**2. 写一个轨迹分析脚本**

```python
def why_chose(thread_id, step):
    """打印第 step 步模型看到的完整输入。"""
    rec = next(r for r in read_logs(thread_id)
               if r["step"] == step and r["kind"] == "model.request")
    for m in rec["messages"]:
        print(f"{m['role']:10s} {m['content'][:100]}")
```

用一次真实失败跑它，看能不能定位原因。

**3. 算一笔存储账**

你的任务平均多少步？每步存多少？跑 1000 次占多大？

超过 1GB 就该考虑分级存储。

---

**下一篇**：[18 · 并发与隔离](18-并发与隔离.md) —— 多个跑起来会互相污染

# 12 · Handoff

> 有些任务一个 agent 做不完，或者不该由它做。
>
> 这一章讲"交接"——把任务交给另一个 agent，或者交给人。

---

## 一、三种交接

| 方向 | 场景 | 例子 |
|---|---|---|
| **Agent → Agent** | 任务需要不同专长 | 会务 agent 把"合同审核"交给法务 agent |
| **Agent → Human** | 超出权限 / 置信度低 | 金额太大，转人工审批 |
| **Human → Agent** | 人做了一半，剩下交给 agent | 人定了场地，让 agent 排日程 |

**第三种最容易被忽略**，但生产里很常见。

---

## 二、Agent → Agent：交接什么

### 不能只传一句话

```python
# 错
handoff(to="legal_agent", message="帮我看看这个合同")
```

**法务 agent 拿到这句话，什么都不知道**：

- 哪个合同？
- 什么业务背景？
- 上一个 agent 已经做了什么？

### 要传四样

| 传什么 | 为什么 |
|---|---|
| **任务目标** | 要达成什么 |
| **已知信息** | 已经查到的事实 |
| **已做的事** | 避免重复劳动 |
| **约束** | 预算、时间、合规要求 |

```python
handoff(
    to="legal_agent",
    task="审核这份场地租赁合同的违约条款",
    facts={
        "venue": "V01 国家会展中心",
        "amount": 8280,
        "date": "2026-11-06",
        "our_standard": "违约条款不超过 30 天租金",
    },
    done=["已确认场地可用", "已确认报价含服务费"],
    constraints={"deadline": "2026-11-03", "must_keep": "不可修改付款方式"},
)
```

**"已做的事"最容易被漏**——不传的话，下一个 agent 会把同样的查询再做一遍。

### 一个关键决定：传全量还是摘要

| 方式 | 优点 | 缺点 |
|---|---|---|
| **全量传** | 信息完整 | 上下文爆炸 |
| **只传结论** | 干净 | 丢失推理过程 |
| **传摘要 + 原始引用** | 折中 | 要设计摘要格式 |

**我们的选择**：只传结论，但保留一个"来源"字段指向原始记录。

```python
{
    "conclusion": "V01 可用，8280 元含服务费",
    "source_ref": "thread:t1/step:5",     # ← 出问题能回去查
}
```

**代价**：下一个 agent 看不到推理过程，出问题要单独查原始 thread。

---

## 三、Handoff prompt：怎么让模型决定"交给谁"

### 最简单的形态

```python
HANDOFF_PROMPT = """你是会务助手。

如果遇到以下情况，把任务交给对应的专员：

| 情况 | 交给 |
|---|---|
| 涉及合同条款、法律责任 | legal_agent |
| 金额超过 5 万 | finance_agent |
| 涉及外宾接待、翻译 | protocol_agent |
| 你自己能处理的 | 不要交接，直接做 |

交接时必须说明：任务目标、已知信息、已经做了什么。

如果拿不准该不该交接，先问用户。"""
```

**注意最后一句**：拿不准时问人，别猜。

### 更可控的形态：用工具表达交接

```python
@tool
def transfer_to_legal(reason: str, context: str) -> str:
    """把任务转交给法务专员。

    什么时候该用：
        涉及合同条款解释、违约责任、合规风险。
    什么时候不该用：
        只是问"合同在哪下载"这种流程问题，自己答。

    Args:
        reason: 为什么要转（一句话）
        context: 已知信息和已做的事（结构化文本）
    """
    return do_handoff("legal_agent", reason, context)
```

**为什么用工具而不是提示词**：

| | 提示词 | 工具 |
|---|---|---|
| 可控性 | 低（模型自由发挥） | 高（参数有 schema） |
| 可观测 | 只能看日志 | 有 `tool.executed` 事件 |
| 可拦截 | 难 | 策略层能拦 |

**推荐用工具**——交接是个重要动作，应该有记录、能审计。

**跑出来是什么**：

```
step 4  agent  → transfer_to_legal(
                   reason="违约条款超过标准",
                   context="V01/8280元/11-06；标准是30天租金，对方要60天")
        judge  → allow
        execute → {"handoff_id": "h001", "to": "legal_agent"}
step 5  （任务转到 legal_agent 的 thread）
```

---

## 四、Agent → Human：什么时候交给人

### 五个明确信号

| 信号 | 例子 |
|---|---|
| **超出权限** | 金额 > 审批阈值 |
| **置信度低** | 检索结果相关度都 < 0.5 |
| **不可逆** | 删除、发布、付款 |
| **规则冲突** | 两个政策要求相反 |
| **用户要求** | "转人工" |

### 和前几章的关系

**这不是新东西，是第 7 章的 interrupt 的延伸**。

区别：

| | interrupt | handoff to human |
|---|---|---|
| 目的 | 等人**确认**一个动作 | 让人**接管**整个任务 |
| 之后 | 程序继续 | 程序停下，人接手 |
| 例子 | "确认下单？" | "这个合同我看不懂，你来" |

### 交接时要给什么

**给人看的和给 agent 看的不一样**：

```python
def escalate_to_human(reason, context, trace_ref):
    """把任务转给人。

    人不像 agent 会自己查上下文，所以要把关键信息摊开。
    """
    return {
        "why": reason,                    # 为什么转
        "summary": context["summary"],    # 一句话说清现状
        "decisions_so_far": context["done"],   # 已经做了什么决定
        "blocking_question": context["question"],  # 卡在哪
        "trace": trace_ref,               # 完整轨迹在哪
    }
```

**"卡在哪"最关键**——不写这个，人接手后要重新理解一遍。

**反例**：

```
❌ "任务失败，请人工处理"
```

**正例**：

```
✅ 转人工原因：合同违约条款（60 天租金）超过公司标准（30 天）

已确认：V01 可用、报价 8280 含服务费、日期 11-06
已做决定：接受场地、接受价格
卡在：违约条款要法务判断能否接受
完整轨迹：thread t1
```

---

## 五、Human → Agent：人做一半交给 agent

### 最常见的场景

人在系统里填了一半表单，剩下的让 agent 补。

```python
# 人已经填了这些
partial = {
    "venue_id": "V01",
    "date": "2026-11-06",
    "headcount": 50,
    # 缺：start_time, hours, purpose
}

# agent 接手
agent.complete(partial)
```

### 关键：区分"人定的"和"agent 猜的"

```python
{
    "venue_id": {"value": "V01", "source": "human", "locked": True},
    "hours": {"value": 4, "source": "agent", "locked": False},
}
```

**`locked: True` 的字段，agent 不能改**——即使它算出来更优的方案。

**为什么重要**：人已经确认过的东西，agent 改掉会让人失去信任。

---

## 六、四个坑

### 坑一：交接丢了"已做的事"

**症状**：下一个 agent 把同样的查询又做一遍。

**代价**：多花 token、多花时间，还可能得出不同结论（因为查询时机不同）。

**修法**：交接时必须带 `done` 字段。

### 坑二：交接循环

```
agent A → agent B → agent A → agent B → ...
```

**原因**：两个 agent 都认为"这不归我管"。

**修法**：

```python
if handoff_count > 3:
    escalate_to_human("交接次数超限，可能职责划分有问题")
```

**和活锁检测是一回事**（第 4 章）——只是层级从"工具调用"上升到"agent 交接"。

### 坑三：交接时上下文截断

**症状**：下一个 agent 说"信息不足"。

**原因**：传摘要时把关键约束截掉了。

**修法**：交接的字段要显式定义，不能靠"自动摘要"。

```python
class HandoffPayload:
    task: str                    # 必填
    facts: dict                  # 必填
    done: list[str]              # 必填
    constraints: dict            # 必填（可以是空）
    source_ref: str              # 必填
```

**五个字段都必填**，缺一个就报错，别让它悄悄过去。

### 坑四：人接手后 agent 还在跑

**症状**：转人工了，但 agent 那一轮还在继续调工具。

**修法**：交接 = 中止当前轮。

```python
def do_handoff(to, reason, context):
    cancel_current_turn()        # ← 先停
    create_handoff_task(to, reason, context)
    return {"handoff_id": ...}
```

**这条和第 7 章的取消是同一套机制**。

---

## 七、我们为什么没做

**单 agent 能做完，不需要交接。**

但如果要做，最小实现是：

```python
@tool
def escalate(reason: str, blocking_question: str) -> str:
    """把任务转给人。

    什么时候该用：金额超 5 万、或你不确定该怎么处理。
    什么时候不该用：只是需要用户确认一个动作（那用 interrupt）。
    """
    return json.dumps({
        "status": "escalated",
        "reason": reason,
        "question": blocking_question,
    })
```

**注意它和 `interrupt` 的区别**：

- `interrupt`：停下来问，等答复后**继续做**
- `escalate`：停下来，**交给人做**

---

## 小结

| 问题 | 答案 |
|---|---|
| 三种交接 | Agent→Agent / Agent→Human / Human→Agent |
| 交接传什么 | 目标、已知、已做、约束、来源 |
| 用提示词还是工具 | **工具**——可观测、可拦截 |
| 和人交接给什么 | 为什么转、卡在哪、已做什么 |
| 人做的部分 | 要 `locked`，agent 不能改 |
| 四个坑 | 丢上下文、交接循环、截断、没停当前轮 |

---

## 动手练

**1. 判断该不该交接**

你的任务需要不同专长吗？

- 需要（合同 + 技术 + 财务）→ 交接
- 不需要（都是同一类判断）→ 别交接，加工具就行

**2. 写一个交接工具**

按第 3 节的模板，写 `transfer_to_xxx`，包含"何时该用"和"何时不该用"。

**3. 测试交接循环**

让两个 agent 互相觉得"不归我管"，看多久会循环。

加一个次数上限，验证它会被拦住。

---

**下一篇**：[13 · 多 Agent](13-多Agent.md) —— 什么时候值得

# 10 · Ontology

> 第 9 章的 RAG 让 agent 能"找到文档里的答案"。
>
> 但有些知识不在文档里，在**业务结构**里——这一章讲怎么把它交给 agent。

---

## 一、RAG 解决不了什么

### 两种失败

**失败一：找得到，但读错**

```
文档说："V01 场地容量 60 人，但超过 50 人需要额外申请消防"
Agent 答："V01 可以坐 60 人，可以直接订"
```

**它读到了，但没理解"超过 50 要申请"是个约束。**

**失败二：根本没在文档里**

```
用户问："这个订单涉及的场地属于哪个展馆？展馆有没有消防限制？"
```

**这类"跨实体推理"的问题，文档里没有现成答案**——要顺着关系查。

### 两种知识的区别

| | 文档知识 | 结构化知识 |
|---|---|---|
| 形态 | 段落、章节 | 实体、关系、规则 |
| 谁给的 | 人写的说明 | 业务模型 |
| 适合问 | "政策是什么" | "哪些场地能满足这个条件" |
| 工具 | RAG | Ontology / 知识图谱 |

**一句话**：

> **RAG 让 agent 读到答案，ontology 让 agent 不会读错。**

---

## 二、四个东西，分工不是并列的

很多资料把它们混着讲，实际上各管一段。

```
OWL2    →  定义"什么是场地、什么是档期、它们怎么关联"    （建模）
RDF     →  实际数据的三元组形式                          （存储格式）
SHACL   →  定义"一条合法订单必须有什么"                  （验证）
Fuseki  →  存 RDF、提供 SPARQL 查询端点                  （服务）
```

### 一条铁律：OWL 不是验证器

**这是最容易踩的坑。**

OWL 是**开世界语义**（open-world）：

> 图里没有提到"审批"，**不能**推出"没有审批"。
> 只能说"不知道有没有"。

所以你不能用 OWL 写这种规则：

```
如果 没有审批 就 拒绝  ← OWL 做不到
```

**运行时护栏必须用 SHACL**——它是**闭世界**：

```
sh:minCount 1   ← 少于一个就是违规，没有"可能还有别处"的余地
```

**这个分工要记牢**：

| | OWL | SHACL |
|---|---|---|
| 世界假设 | 开世界（不知道≠没有） | 闭世界（没写就是没有） |
| 用途 | 建模、推理 | 验证、边界 |
| 能当护栏吗 | **不能** | 能 |

### 一个具体的会务本体

**建模部分（OWL）**：

```turtle
@prefix ex:   <http://example.org/venue#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

ex:Venue a owl:Class ;
    rdfs:label "场地" .

ex:Hall a owl:Class ;
    rdfs:label "展馆" .

ex:Booking a owl:Class ;
    rdfs:label "订单" .

# 场地属于某个展馆
ex:belongsToHall a owl:ObjectProperty ;
    rdfs:domain ex:Venue ;
    rdfs:range  ex:Hall .

# 场地容量
ex:capacity a owl:DatatypeProperty ;
    rdfs:domain ex:Venue ;
    rdfs:range  xsd:integer .

# 订单订的是哪个场地
ex:booksVenue a owl:ObjectProperty ;
    rdfs:domain ex:Booking ;
    rdfs:range  ex:Venue .
```

**实例数据（RDF）**：

```turtle
ex:V01 a ex:Venue ;
    ex:capacity 60 ;
    ex:belongsToHall ex:HallA .

ex:HallA a ex:Hall ;
    rdfs:label "国家会展中心 A 馆" .

ex:BK001 a ex:Booking ;
    ex:booksVenue ex:V01 .
```

**有了这个，就能回答 RAG 答不了的问题**：

```sparql
# 这个订单的场地属于哪个展馆？
SELECT ?hall WHERE {
  ex:BK001 ex:booksVenue ?venue .
  ?venue ex:belongsToHall ?hall .
}
```

**跑出来是什么**：

```
?hall = ex:HallA
```

### 验证部分（SHACL）

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .

# 一条可执行的订单，必须有什么
ex:BookableOrderShape a sh:NodeShape ;
    sh:targetClass ex:Booking ;
    sh:property [
        sh:path ex:booksVenue ;
        sh:class ex:Venue ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] ;
    sh:property [
        sh:path ex:hasApproval ;
        sh:class ex:ValidApproval ;
        sh:minCount 1 ;
        sh:message "没有审批，不能执行" ;
    ] .

# 场地本身的数据完整性
ex:VenueShape a sh:NodeShape ;
    sh:targetClass ex:Venue ;
    sh:property [
        sh:path ex:capacity ;
        sh:minCount 1 ;
        sh:datatype xsd:integer ;
        sh:minInclusive 1 ;
    ] .
```

**跑一遍验证**，不合格会返回结构化的违规报告：

```
[Violation] BK002
  Path: ex:hasApproval
  Message: 没有审批，不能执行
  Severity: sh:Violation
```

**这个报告可以直接返回给 agent**——它知道缺什么，可以自己去补，或者告诉用户。

---

## 三、为什么这比写在 prompt 里强

### 对比

| | 写在 prompt | 写在 SHACL |
|---|---|---|
| 谁能改 | 只有开发者 | 业务方也能审 |
| 会被绕过吗 | 模型可能忽略 | **不能**，验证在代码里 |
| 能审计吗 | 只能看日志 | 能说出违反了哪条 shape |
| 加一条规则 | 改 prompt，可能影响别的 | 加一个 shape，互不影响 |

### 一个具体场景

**prompt 版**：

```
你是会务助手。下单前必须确认：
1. 场地存在
2. 有审批
3. 金额不超预算
```

**问题**：模型可能漏掉某条，或者"灵活处理"。

**SHACL 版**：

```turtle
ex:BookableOrderShape sh:property [
    sh:path ex:hasApproval ;
    sh:minCount 1 ;
] .
```

**执行前跑一次验证**，不过就拦。模型怎么想都没用。

**这就是第 20 章讲的"模型是不可信输入源"的具体实现。**

---

## 四、工具链

### 建模：Protégé

桌面工具，图形化编辑 OWL。学术界标准。

**新手的第一小时**：装好、打开、建三个类、加两个属性、看它画出图。

### Python 侧：RDFLib

```python
from rdflib import Graph, Namespace, Literal

g = Graph()
g.parse("venue.ttl", format="turtle")

EX = Namespace("http://example.org/venue#")

# 查 V01 的容量
for cap in g.objects(EX.V01, EX.capacity):
    print(f"容量：{cap}")
```

**跑出来是什么**：

```
容量：60
```

**RDFLib 的价值**：不用起服务，Python 里直接操作图。

### 服务：Fuseki

Apache Jena 的 SPARQL 端点。

```bash
# 启动（需要先下载 Jena）
fuseki-server --update --mem /ds
```

**然后就能 HTTP 查**：

```bash
curl -G http://localhost:3030/ds/query \
  --data-urlencode 'query=SELECT * WHERE { ?s ?p ?o } LIMIT 5'
```

**什么时候需要 Fuseki**：多个服务要查同一份本体时。单机脚本用 RDFLib 就够。

### 2026 的新动向：Ontology + MCP

**这个值得注意**——本体正在变成 agent 的 API。

```
以前：人在 Protégé 里编辑本体
现在：agent 通过 MCP 查询本体、遍历关系、调用动作
```

**例子**：

| 项目 | 做什么 |
|---|---|
| Palantir Ontology MCP | 把本体暴露成 MCP 工具，agent 能查对象、走关系、执行动作 |
| Open Ontologies MCP Server | 35 个工具，让 agent 自己生成和验证 OWL 本体 |

**这个方向的意义**：

> 本体不再是"给人看的文档"，而是"给 agent 用的接口"。

**但要注意**：这是 2026 年的新东西，生产案例还少。**别拿它当稳定方案**。

---

## 五、语义层是另一件事

**这两个概念经常被混**，但管的是不同的东西。

| | 语义层 | Ontology |
|---|---|---|
| 管什么 | **指标口径** | **实体和规则** |
| 回答 | "销售额是多少" | "哪个客户、哪份合同、能不能执行" |
| 典型问题 | 三个 Agent 的"营收"必须同一个数 | 销售 Agent 只能看金额，不能看卡号 |

**一句话**：

> 语义层回答"多少钱"，ontology 回答"这是什么、能做什么"。

### 语义层的 2026 工具

| 工具 | 特点 |
|---|---|
| dbt Semantic Layer / MetricFlow | 已经在用 dbt 的首选 |
| Cube | 开源，MCP server 支持 |
| **WrenAI** | 开源，MDL 定义语言，20+ 数据源 |
| **SLayer**（2026-09 开源） | MIT，可嵌 Python / MCP / REST |
| Snowflake / Databricks 原生 | 单一平台时直接用 |

**共同点**：把"指标怎么算"从 prompt 里拿出来，定义一次，处处复用。

**这正好解决第 6 章讲的问题**——同一个概念在三个 prompt 里有三种说法。

---

## 六、什么时候不该上

**这一节比前面都重要**，因为 ontology 的开发成本很高。

### 四个"不该上"的信号

| 信号 | 为什么 |
|---|---|
| **实体少于 20 个** | 直接写 Python 类型 + Pydantic 校验更快 |
| **关系是简单的一对多** | 关系数据库够用 |
| **没有推理需求** | 不需要"从 A 推出 B"，上本体是浪费 |
| **团队没人懂 SPARQL** | 维护成本会压垮收益 |

### 四个"该上"的信号

| 信号 | 例子 |
|---|---|
| **多系统口径不一致** | 三个 Agent 对"场地可用"判断不同 |
| **需要跨实体推理** | "这个订单的场地属于哪个展馆、展馆有无消防限制" |
| **权限要细到语义层** | "财务能看金额，不能看卡号" |
| **规则要被审计** | 拒绝订单时要能说出违反了哪条 |

### 我们的情况

**没用，也不该用**：

| 维度 | 我们的规模 |
|---|---|
| 工具 | 5 个 |
| 实体 | 4 个（场地、档期、报价、订单） |
| 规则 | 5 条（写在策略层） |
| 关系 | 一对一（一个订单一个场地） |

**用 Python dataclass + Pydantic 就够**——`World` 对象里几个字典，验证用 `if` 判断。

**什么时候会需要**：如果要做"跨展馆的会务调度"（场地 → 展馆 → 档期 → 相邻展馆的冲突），关系变复杂，才值得上本体。

---

## 七、Pydantic 在其中的位置

**别把它和 OWL/SHACL 混**——它管的是**应用层接口**。

| | SHACL | Pydantic |
|---|---|---|
| 管什么 | 图数据的完整性 | Python 对象的结构 |
| 在哪跑 | 验证服务 | 代码里 |
| 典型用途 | "这个订单缺审批" | "这个 API 请求少传了字段" |

**组合用法**：

```python
from pydantic import BaseModel, Field

class BookingRequest(BaseModel):
    venue_id: str = Field(pattern=r"^V\d{2}$")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    hours: int = Field(ge=2, le=8)

# ① 应用层：Pydantic 挡掉格式错误
req = BookingRequest(**raw)

# ② 转成 RDF，写进图
g.add((EX[req.venue_id], EX.booksOn, Literal(req.date)))

# ③ 语义层：SHACL 验证业务规则
report = validate(g, shapes)
if not report.conforms:
    return report.violations  # ← 返回给 agent
```

**三层的分工**：

```
Pydantic  →  参数格式对不对（字符串 vs 整数）
SHACL     →  业务规则满不满足（有没有审批）
策略层    →  这个动作允不允许（预算够不够）
```

**每一层管不同的东西，不能互相替代。**

---

## 小结

| 问题 | 答案 |
|---|---|
| RAG 和 ontology 的区别 | RAG 找信息，ontology 理解含义 |
| OWL 能当验证器吗 | **不能**。开世界语义，要用 SHACL |
| 四个东西的分工 | OWL 建模 / RDF 存储 / SHACL 验证 / Fuseki 服务 |
| 语义层是什么 | 指标口径，和 ontology 不是一回事 |
| 什么时候不该上 | 实体少、关系简单、无推理需求、没人懂 SPARQL |
| Pydantic 的位置 | 应用层参数校验，不是本体 |
| 2026 新动向 | 本体暴露成 MCP，让 agent 直接用 |

---

## 动手练

**1. 判断该不该上**

数一下你的实体和关系：

- 实体 < 20 且关系简单 → 别上
- 需要跨三层以上的关系推理 → 值得考虑

**2. 写一个最小本体**

用 Protégé 建三个类、两个关系、三个属性。

**重点看**：它能不能回答"这个订单的场地属于哪个展馆"。

**3. 写一条 SHACL**

给"订单"加一条：必须有审批。

然后故意造一个没审批的实例，看验证报告长什么样。

**4. 对比 prompt 版**

把同一条规则写在 prompt 里，让模型跑一遍。

**看它会不会漏**——这就是为什么要 SHACL。

---

**下一篇**：[11 · Memory 与 Skills](11-Memory与Skills.md) —— 跨会话记住，跨项目复用

# 附录 B · 数据来源

> 正文里引用的论文、基准和实践总结。
>
> **核对程度**：论文核对了摘要页，基准核对了公开结果页。**没有逐个复核原始论文。**
> 要用在生产决策上，建议回原文。

---

## 完整清单

| 主题 | 来源 |
|---|---|
| workflow vs agent | Anthropic, *Building effective agents* |
| Agent 五模式 | aihive 2026 综述、aisoftwaredev.io、techademy |
| 上下文遮蔽（52% 成本降幅） | JetBrains, *The Complexity Trap*, **arXiv 2508.21433** |
| context-rot（18 模型全退化） | Chroma 2025 研究 |
| 压缩阈值 60-70% | agentnative.dev compaction 模式总结 |
| ACON 压缩（26-54% token 降幅） | **ICML 2026, arXiv 2510.00615** |
| RAG 基准（48/69/99%） | TigerGraph Agentic GraphRAG 基准, 2026-10 |
| RAG 幻觉率对照 | Blue Guardrails, PlaceboBench 2026 |
| MCP 规范 2026-07-28 | modelcontextprotocol.io、dataaihub 解读 |
| MCP 企业架构 | veluralabs 2026 指南 |
| 工具设计七条 | creativegenius 2026 实践指南 |
| Plan-Execute 降本 40-60% | aihive 2026 企业实践报告 |

**注意**：行业综述类来源（aihive / veluralabs / creativegenius）是二手总结，数字可能有出入。
论文和公开基准（arXiv、TigerGraph、Blue Guardrails）可信度更高。

**我引用的数字没有逐个复核原始论文**，只核对了摘要页。如果要用在生产决策上，建议回原文。


---

## 可信度分级

| 类型 | 例子 | 可信度 |
|---|---|---|
| 论文（有 arXiv 编号） | JetBrains 2508.21433 | 高 |
| 公开基准（有数据集和代码） | TigerGraph Agentic GraphRAG | 高 |
| 企业实践总结 | aihive / veluralabs | 中（二手） |
| 媒体转述 | 各类博客 | 低 |

**正文里标「实测」的，是我们自己跑的。**

---

## 一处必须说明的矛盾

关于 RAG，我搜到两份结论相反的基准：

| 基准 | 任务类型 | 结论 |
|---|---|---|
| TigerGraph | 聚合 / 多跳 | Agentic 最好（99% vs 48%） |
| Blue Guardrails | 医药事实问答 | Agentic 幻觉率最高（30.4% vs 8.7%） |

**不能简单说「agentic RAG 更好」。**

agentic 检索只在「证据分散、需要逐层确认」时有价值；单点事实题上，多轮检索是纯成本 + 纯噪音。

**两份都列出来，因为它们同等重要。**

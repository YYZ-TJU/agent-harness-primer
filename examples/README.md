# 示例代码

12 个能跑的例子。**不需要 API key，不花钱，结果可预测。**

## 为什么用"假模型"

真模型要 key、要钱、每次结果还不一样。

教学最怕"结果不稳定"——你改一个参数，分不清是改动生效了还是模型抽风。

`fake_llm.py` 行为完全确定：同样的输入，永远同样的输出。

## 怎么跑

```bash
cd agent-harness-primer
pip install -r requirements.txt

python examples/ch1_langchain/e01_hello.py
```

## 第一章：LangChain

| 文件 | 教什么 |
|---|---|
| `e01_hello.py` | 模型是函数：消息列表进，一条消息出 |
| `e02_tool.py` | **工具三步**：模型说要调 → 你执行 → 结果回填 |
| `e03_multi_turn.py` | 模型没记忆，每次重传历史，越聊越贵 |
| `e04_stream.py` | 一次性 vs 流式 |

## 第二章：LangGraph

| 文件 | 教什么 |
|---|---|
| `e01_graph.py` | 图 = 流程图（State / 节点 / 边） |
| `e02_reducer.py` | 覆盖 vs 追加（选错不报错） |
| `e03_branch.py` | 条件边（漏分支编译时不报） |
| `e04_loop.py` | 循环（退出条件写错会跑死） |
| `e05_pause.py` | interrupt 会让节点**重跑** |

## 第三部分：概念演示（不调模型）

| 文件 | 教什么 |
|---|---|
| `e01_trajectory.py` | 从轨迹里查"它为什么这么决定" |
| `e02_multi_agent_math.py` | 3 个 90% 串行只有 73% |
| `e03_handoff.py` | 交接漏一个字段会怎样 |

**这三个不调模型**——它们演示的是"结构"和"算术"，不需要 AI。

跑法一样：

```bash
python examples/ch3_concepts/e01_trajectory.py
```

## 换成真模型

改 `fake_llm.py`，换成：

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.environ["DEEPSEEK_API_KEY"],
)
```

**注意**：真模型行为不确定，例子里的输出会变。

## 几个值得改的地方

| 改什么 | 看什么 |
|---|---|
| `e01_hello.py` 里 SystemMessage 的内容 | 输出不变——假模型不看内容 |
| `e04_stream.py` 的 `chunk_size` 从 6 改成 20 | 反馈颗粒度变粗 |
| `e02_reducer.py` 把 `Annotated` 去掉 | 从"追加"变"覆盖" |
| `e05_pause.py` 在 interrupt 前加个 print | 恢复时打印两次 |

改坏了大不了重跑。

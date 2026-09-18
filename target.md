# 第一阶段：完成 RAG 的学习

状态：已完成。

本阶段采用“直接使用 LlamaIndex 搭建可运行系统，再逐层拆解和替换内部组件”的学习方式。不提前重复实现完整框架，但必须理解每一层如何影响检索和回答质量。

最终成果是一个简单但完整的 RAG 系统：支持数据写入、检索、带来源回答，同时提供普通 HTTP API 和标准 MCP 接口。

## 阶段 1：使用 LlamaIndex 跑通最小 RAG

使用以下核心组件完成第一条端到端链路：

- LlamaIndex：RAG 主框架。
- Qdrant：向量数据库。
- 本地 Embedding 模型：生成查询和文档向量。
- Ollama LLM：根据检索结果生成答案。

需要跑通的数据流：

```text
Markdown 文件
  -> LlamaIndex 读取
  -> 文档切块
  -> Embedding
  -> 写入 Qdrant
  -> Retriever 检索
  -> LLM 生成答案
```

验收目标：

- 可以导入 Markdown 文档。
- 可以重复执行索引流程。
- 可以输入问题并获得答案。
- 答案包含可核查的来源信息。

## 阶段 2：观察并理解 LlamaIndex 内部过程

系统跑通后，逐项检查框架内部产生的数据：

- `Document` 表示什么。
- 文档被切成了哪些 `Node`。
- 每个 Node 保存了哪些 Metadata。
- Embedding 的维度、归一化方式和相似度计算方式。
- 查询实际召回了哪些 Chunk。
- 每个召回结果的相似度分数。
- 最终传给 LLM 的 Context 内容。

验收目标：能够解释一次查询从用户问题到最终答案的完整路径，并能判断错误来自索引、检索还是生成阶段。

## 阶段 3：学习 Embedding 与检索评估

围绕已经运行的系统学习以下概念：

- Query Embedding 与 Document Embedding。
- 对称检索与非对称检索。
- Instruction-aware Embedding。
- 向量归一化与余弦相似度。
- Top-K、Recall@K、MRR 和 NDCG。
- Hard Negative。
- Chunk 大小和重叠范围对召回结果的影响。

建立一个小型 Golden Dataset，为每个问题标记预期召回的文档或代码块。后续所有检索策略调整都必须通过同一数据集比较。

验收目标：能够通过评估结果选择 Embedding 模型和检索参数，而不是只依赖公开排行榜或主观观察。

## 阶段 4：逐步替换默认实现

在保留 LlamaIndex 主框架的前提下，依次替换或扩展默认模块：

1. 默认文本切块替换为 Markdown 结构切块。
2. 为代码内容加入基于函数、类和模块边界的结构化切块。
3. Dense 检索升级为 Dense + BM25/Sparse 混合检索。
4. 使用 RRF 融合多路召回结果。
5. 加入 Reranker 对候选结果重新排序。
6. 加入 Parent-child retrieval 和相邻代码块扩展。
7. 加入 Project、Repository、Path、Language 等 Metadata 过滤。
8. 让答案返回文件路径、行号、检索分数和置信度。

每替换一个模块，都要记录修改前后的检索指标和代表性失败案例。

验收目标：系统不仅能回答问题，还能解释为什么选择这些上下文，并能通过测试证明检索质量有所改善。

## 阶段 5：整理核心服务边界

将 RAG 能力整理为独立的应用服务，避免 HTTP 和 MCP 分别实现两套逻辑：

```text
RAGService
├── ingest()
├── search()
├── answer()
└── delete()
```

内部职责建议拆分为：

- `IngestionService`：读取、切块、生成 Metadata、Embedding 和写入。
- `RetrievalService`：Dense、Sparse、过滤和融合。
- `RerankingService`：候选结果重排。
- `AnswerService`：构建 Context、调用 LLM、生成答案和引用。

验收目标：核心服务可以脱离 Web 框架独立测试。

## 阶段 6：提供普通 HTTP API

使用 FastAPI 和 Pydantic 提供面向人及普通程序的接口：

```text
POST   /v1/documents
DELETE /v1/documents/{id}
POST   /v1/index
POST   /v1/search
POST   /v1/answer
GET    /v1/collections
GET    /health
```

其中 `/v1/search` 只返回检索结果，`/v1/answer` 才调用 LLM。这样可以分别诊断检索错误和生成错误。

验收目标：可以通过 OpenAPI/Swagger 完成写入、搜索和问答流程。

## 阶段 7：提供标准 MCP 接口

使用官方 MCP Python SDK，通过 Streamable HTTP 提供 `/mcp` 端点。MCP 与 HTTP API 共用同一个 `RAGService`。

第一版提供以下能力：

```text
Tools
├── search_knowledge
├── answer_with_sources
└── get_document_chunk

Resources
├── rag://collections
└── rag://documents/{document_id}
```

第一版不向 Agent 开放任意知识库写入能力。后续需要加入写入工具时，再补充认证、权限与审批机制。

验收目标：兼容标准 MCP 客户端，Agent 可以发现并调用工具，获得结构化检索结果和来源信息。

## 阶段 8：完成端到端验证

最终验证范围：

- 文档写入、更新、删除和重复索引。
- Dense、Sparse、Hybrid 和 Reranker 的检索质量对比。
- Recall@K、MRR、NDCG、引用正确率和无答案检测。
- HTTP API 契约测试。
- MCP 工具发现与调用测试。
- 回答中的引用可以追溯到原始文件和位置。
- 更换 Embedding 模型、LLM 或向量数据库适配器时，不影响对外接口。

# 第二阶段：Agent 学习（LangChain、LangGraph）

目标：做出一个能够自主调用第一阶段 RAG MCP 的简单 Agent。

## 1. LangChain Agent

- 理解 Message、Tool、Tool Call 和 Structured Output。
- 使用当前的 `create_agent` 创建单 Agent。
- 先用一个简单工具跑通“判断、调用、返回结果”。

验收：Agent 能正确选择工具，并返回结构化结果。

## 2. LangGraph

- 理解 State、Node、Edge 和条件分支。
- 将 Agent 拆成“判断是否检索 → 调用工具 → 生成回答”三个节点。
- 加入最大循环次数和失败处理。

验收：能够查看每一步状态，并解释 Agent 为什么调用工具。

## 3. 接入 RAG MCP

- 通过标准 MCP 客户端发现第一阶段提供的工具。
- 将 `search_knowledge` 和 `answer_with_sources` 提供给 Agent。
- 最终回答保留文件路径和来源。

验收：Agent 可以通过 MCP 查询知识库，并输出带来源的答案。

## 4. 最终验证

- 普通问题不调用 RAG。
- 知识库问题会调用 RAG。
- 无证据时明确说明无法回答。
- 工具失败时返回清晰错误，不无限重试。

最终成果：一个简单、可测试、可观察的单 Agent；暂不学习多 Agent。

# 当前项目架构

以下结构是当前实现约定。RAG 服务只负责文档处理、索引和检索，不负责调用 LLM 生成答案；前文遗留的 `answer`、`AnswerService` 和 `answer_with_sources` 设计不再采用。答案生成由外部 Agent 完成。

```text
rag/
├── AGENTS.md
├── target.md
├── pyproject.toml
├── README.md
├── .env.example
├── prisma/
│   ├── schema.prisma
│   └── migrations/
├── src/rag/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── core/
│   │   ├── document_processing/
│   │   │   ├── parser.py
│   │   │   ├── cleaner.py
│   │   │   └── chunker.py
│   │   ├── embedding/
│   │   │   └── embedder.py
│   │   └── retrieval/
│   │       ├── models.py
│   │       ├── vector_search.py
│   │       ├── keyword_search.py
│   │       ├── fusion.py
│   │       └── reranker.py
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── client.py
│   │   │   ├── entities/
│   │   │   │   ├── knowledge_base.py
│   │   │   │   ├── document.py
│   │   │   │   └── chunk.py
│   │   │   └── repositories/
│   │   │       ├── knowledge_base_repository.py
│   │   │       ├── document_repository.py
│   │   │       └── chunk_repository.py
│   │   ├── vector_store/
│   │   │   ├── client.py
│   │   │   ├── entities/
│   │   │   │   ├── vector_record.py
│   │   │   │   └── search_hit.py
│   │   │   └── repositories/
│   │   │       └── vector_repository.py
│   │   └── embedding/
│   │       └── ollama_embedder.py
│   ├── use_cases/
│   │   ├── ingest_document.py
│   │   ├── delete_document.py
│   │   ├── reindex_document.py
│   │   ├── search_knowledge.py
│   │   ├── get_document_chunk.py
│   │   └── list_knowledge_bases.py
│   └── interfaces/
│       ├── http/
│       │   ├── app.py
│       │   ├── schemas/
│       │   └── routes/
│       │       ├── documents.py
│       │       ├── search.py
│       │       └── knowledge_bases.py
│       └── mcp/
│           ├── server.py
│           └── tools/
│               ├── search_knowledge.py
│               ├── get_document_chunk.py
│               └── list_knowledge_bases.py
└── tests/
    ├── core/
    ├── infrastructure/
    ├── use_cases/
    └── interfaces/
```

## 分层职责

- `core`：文档处理、Embedding 抽象和检索算法等核心逻辑。
- `use_cases`：每个文件完成一个明确的业务动作，并组合 Core 与 Repository。
- `interfaces`：HTTP 和 MCP 的协议转换，不包含业务逻辑。
- `infrastructure`：PostgreSQL、Qdrant 和 Ollama Embedding 等外部服务实现。
- `entities`：跟随拥有这些数据的基础设施模块；没有独立数据结构的模块不建立 `entities`。
- `repositories`：负责对应实体的存取。
- `prisma/schema.prisma`：PostgreSQL 表结构的唯一来源；迁移文件存放于 `prisma/migrations`。

依赖方向：

```text
HTTP / MCP -> use_cases -> core + infrastructure repositories
                              -> PostgreSQL / Qdrant / Ollama Embedding
```

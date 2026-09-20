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
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
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
│   │   │   ├── models.py
│   │   │   ├── entities/
│   │   │   │   ├── document.py
│   │   │   │   └── chunk.py
│   │   │   └── repositories/
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
│   │   └── list_documents.py
│   └── interfaces/
│       ├── http/
│       │   ├── app.py
│       │   ├── schemas/
│       │   └── routes/
│       │       ├── documents.py
│       │       └── search.py
│       └── mcp/
│           ├── server.py
│           └── tools/
│               ├── search_knowledge.py
│               ├── get_document_chunk.py
│               └── list_documents.py
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
- `infrastructure/database/models.py`：SQLAlchemy 2.0 运行时映射与 Alembic Metadata 来源；迁移文件存放于 `alembic/versions`。

依赖方向：

```text
HTTP / MCP -> use_cases -> core + infrastructure repositories
                              -> PostgreSQL / RabbitMQ
Worker     -> RabbitMQ -> PostgreSQL / Ollama Embedding / Qdrant
```

## 文档解析与 Embedding Pipeline

使用 Microsoft MarkItDown 作为文档进入 Embedding Pipeline 的统一解析环节。它负责把 PDF、Word、Excel、PowerPoint、HTML 等受支持的原始文件转换为 Markdown，使后续清洗和切块不需要分别处理每种文件格式。

```text
原始文件
  -> MarkItDown 转换为 Markdown
  -> cleaner 清洗和规范化
  -> chunker 按 Markdown 结构切块
  -> 生成 Chunk Metadata
  -> PostgreSQL 保存 Document 和 Chunk
  -> RabbitMQ 发布索引任务
  -> Worker 调用 Ollama Embedding 生成向量
  -> Qdrant 只写入 Chunk ID 和向量
```

- `core/document_processing/parser.py` 封装 MarkItDown，对上层提供统一的文档解析接口。
- MarkItDown 只负责格式转换和尽量保留标题、列表、表格、链接等文档结构，不负责清洗、切块、Embedding 或检索。
- 原生 Markdown 和普通文本也通过同一解析接口进入后续流程，避免 use case 感知具体文件格式。
- MarkItDown 的输出先经过 `cleaner` 和 `chunker`，不能直接生成 Embedding。
- 解析失败时终止本次索引，不向 RabbitMQ 发布任务，也不向 Qdrant 写入不完整数据，并通过 Document 状态和错误字段保留可诊断信息。
- 第一版只启用项目明确支持且有测试覆盖的格式；新增格式时需要补充解析和端到端索引测试。

验收目标：能够输入至少一种非 Markdown 文档，通过 MarkItDown 转换、清洗、切块、Embedding 后写入 Qdrant；转换后的标题、列表或表格结构可以在 Chunk 内容中检查，解析失败不会产生残留向量。

## 数据结构约定

当前以单个文档作为最大业务单位，不建立 Knowledge Base：

```text
documents 1 ── N chunks
```

### Document

`documents` 是文档事实数据的根实体。MarkItDown 转换后的完整 Markdown 文本保存在 PostgreSQL，用于重新清洗和切块。

```text
documents
├── id               UUID PK
├── source_uri       TEXT UNIQUE
├── title            TEXT NULL
├── source_type      ENUM
├── content          TEXT
├── content_hash     TEXT
├── current_version  INT DEFAULT 1
├── status           ENUM
├── last_error       TEXT NULL
├── metadata         JSONB DEFAULT {}
├── created_at       TIMESTAMPTZ
└── updated_at       TIMESTAMPTZ
```

- `content` 保存 MarkItDown 的完整 Markdown 输出，不保存 Embedding。
- `content_hash` 根据 `content` 计算，用于识别内容是否变化和避免无效重建。
- `status` 使用 `pending`、`indexing`、`ready`、`failed`、`deleting`、`deleted`。
- `last_error` 保存最近一次处理失败的可诊断错误；成功后清空。

### Chunk

`chunks` 保存切块后的文本和引用信息，是 Qdrant 向量的 PostgreSQL 事实来源。

```text
chunks
├── id            UUID PK
├── document_id   UUID FK -> documents.id
├── version       INT
├── chunk_index   INT
├── content       TEXT
├── start_line    INT NULL
├── end_line      INT NULL
├── token_count   INT NULL
├── metadata      JSONB DEFAULT {}
├── active        BOOLEAN
└── created_at    TIMESTAMPTZ
```

- `id` 同时作为 Qdrant Point ID。
- 同一文档版本中 `chunk_index` 从 `0` 开始，并使用 `UNIQUE(document_id, version, chunk_index)` 保证顺序唯一。
- `start_line` 和 `end_line` 使用从 `1` 开始且包含边界的原文行号；无法稳定定位时允许为空。
- 文档重建成功后，旧 Chunk 必须停用，其对应的 Qdrant Point 必须物理删除。

### Qdrant Point

Qdrant 使用单个 `rag_chunks` Collection，只保存 Chunk ID 和 Dense Vector，不保存 Payload。

```text
rag_chunks Point
├── id      UUID = chunks.id
└── vector  FLOAT32[embedding_dimension]
```

- `embedding_dimension` 由选定的 Embedding 模型决定，Collection 中所有向量维度必须一致。
- 相似度度量遵循 Embedding 模型要求；没有特别要求时使用 `Cosine`。
- Qdrant 搜索只返回 `chunk_id` 和 `score`，再按 ID 到 PostgreSQL 批量读取 `chunks.content` 及来源信息，并按 Qdrant 排名恢复顺序。
- 因为没有 Payload，Qdrant 不承担 `document_id`、`active`、版本或 Metadata 过滤；无效 Point 必须及时删除。

### RabbitMQ 索引任务拓扑

不建立 `index_jobs` 表。FastAPI 是生产者，Python Worker 是消费者，RabbitMQ 负责索引任务的投递、确认、重投和死信隔离。

```text
Exchange: rag.indexing
├── type: direct
├── durable: true
└── routing keys
    ├── document.ingest
    ├── document.reindex
    └── document.delete

Queue: rag.indexing.jobs
├── durable: true
├── bound to: rag.indexing
└── consumes: document.ingest / document.reindex / document.delete

Dead-letter Exchange: rag.indexing.dlx
├── type: direct
└── durable: true

Dead-letter Queue: rag.indexing.dead
├── durable: true
└── bound to: rag.indexing.dlx
```

- 生产者 Channel 开启 Publisher Confirms，发布持久消息；确认 Broker 接收后 FastAPI 才认为任务已提交。
- 消费者 Channel 使用手动 ACK 和有界 `prefetch_count`；只有 PostgreSQL 状态更新与 Qdrant 操作成功后才 ACK。
- 可恢复错误进行有上限的重试；超过上限后投递到 `rag.indexing.dead`，同时将 `documents.status` 置为 `failed` 并记录 `last_error`。
- 消息体只传递 `document_id`、`operation`、`version` 和必要的重试头，不传递文档正文、Chunk 内容或向量。
- 所有 Worker 操作必须幂等：同一 Chunk 重复写入使用同一 Point ID，重复删除已不存在的 Point 也视为成功。

### 总体约定

- PostgreSQL 是事实来源；Qdrant 只是可从 PostgreSQL 重建的检索索引。
- Embedding 只保存到 Qdrant，不使用 `pgvector`。
- RabbitMQ 是任务传输和暂存层，不是业务事实数据库。
- 当前不建立 `knowledge_bases`、`document_versions`、`index_jobs`；需要组织多个文档时再增加 `collections`。

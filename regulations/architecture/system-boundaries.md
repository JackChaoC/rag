# 系统边界与数据所有权

## 组件职责与依赖方向

> 变更批次：`26-09-19_1`
> 变更来源：`improve-regulations`
> 落地状态：`已实现`
> 实现优先级：`P0`

适用于文档写入、重建、删除和检索主流程。

- HTTP 与 MCP 接口只负责协议转换，不包含文档处理、索引或检索业务逻辑。
- Use Case 负责组合 Core 能力和 Infrastructure Repository；Core 不依赖 FastAPI、MCP、Prisma、RabbitMQ、Qdrant 或 Ollama 的具体客户端。
- FastAPI 进程负责接收请求、解析和切分文档、保存 PostgreSQL 事实数据并向 RabbitMQ 发布索引任务；不得在请求进程中生成 Embedding 或直接写入 Qdrant。
- Python Worker 只通过 RabbitMQ 接收索引任务，并访问 PostgreSQL、Ollama Embedding 和 Qdrant 完成异步索引操作。
- PostgreSQL 是 Document 和 Chunk 的唯一业务事实来源；Qdrant 仅保存可由有效 Chunk 重建的向量索引；RabbitMQ 仅负责消息传输与暂存。
- RAG 服务只负责文档处理、索引和检索，不调用 LLM 生成答案；答案生成由外部 Agent 完成。
- 当前业务最大单位是单个 Document，不建立 Knowledge Base、Collection 业务实体、Document Version 实体或 Index Job 实体。
- 第一版是本地学习系统，不实现认证、授权、多租户、公网部署或任意远程 URL 抓取；`source_uri` 是调用方提供的来源标识，不由服务主动访问。

失败时不得把 RabbitMQ 或 Qdrant 中的临时状态视为业务事实。任何检索结果都必须回到 PostgreSQL 验证对应 Chunk 当前有效。

验收条件：通过依赖检查或测试证明 Core 可脱离外部框架运行；HTTP/MCP 调用同一组 Use Case；FastAPI 进程没有 Embedding 或 Qdrant 写入路径；删除 Qdrant Collection 后能以 PostgreSQL 数据重新建立索引。

权威依据：[`target.md`](../../target.md) 的“当前项目架构”“分层职责”和“总体约定”。

## 运行进程与公开入口

> 变更批次：`26-09-23_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

`uv run rag` 启动单个 Uvicorn/FastAPI 进程，同时提供 HTTP API、健康检查、Swagger、MCP 和静态前端；前端不使用独立开发服务器。

```text
uv run rag
  │
  ├── Uvicorn：127.0.0.1:8000
  │
  └── FastAPI
      ├── /v1/*    HTTP API
      ├── /health  健康检查
      ├── /docs    Swagger
      ├── /mcp     MCP
      └── /ui/*    前端静态文件
```

`frontend/` 必须挂载到 `/ui`，使浏览器页面与 API 保持同源。异步索引消费者不属于该 Web 进程，由 `uv run rag-worker` 单独启动。

权威入口：[`pyproject.toml`](../../pyproject.toml)、[`src/rag/main.py`](../../src/rag/main.py)、[`src/rag/interfaces/http/app.py`](../../src/rag/interfaces/http/app.py) 和 [`src/rag/worker/worker.py`](../../src/rag/worker/worker.py)。

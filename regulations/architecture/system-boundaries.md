# 系统边界与数据所有权

## 依赖注入与资源生命周期

> 变更批次：`26-09-27_0`
> 变更来源：`improve-regulations`
> 落地状态：`待实现`
> 实现优先级：`P0`

- 使用 `dependency-injector` 的 `DeclarativeContainer` 统一声明 HTTP、MCP 和 Worker 的依赖图；每个运行进程创建自己的容器。
- 容器位于 `src/rag/containers/`：ApplicationContainer 只组装子容器；Resources 为最底层，Repositories 只依赖 Resources，Services 只依赖 Repositories，UseCases 只依赖 Services。Worker Handler 只把消息协议转换后调用 Use Case；除消费入口取得 Broker 外，不得绕过 Use Case 直接编排业务依赖。子容器用 DependenciesContainer 显式声明下层依赖，共享底层 provider。
- HTTP 依赖路径为 `ApplicationContainer.use_cases.*`，Worker 从 `container.worker.*` 解析 Handler 和 Dispatcher，连接从 `container.resources.*` 解析；资源初始化及生命周期函数统一位于 `containers/resources.py`。
- 配置由 Pydantic Settings 校验后载入 Configuration；Database、RabbitBroker、Qdrant 和 Ollama Embedder 使用 Resource。无请求状态的 Repository、Service、Use Case、Handler 和 Dispatcher 使用容器级 Singleton。Parser 及持有它的 Ingest/Reindex Use Case 保留 Factory，避免跨解析线程共享 MarkItDown；每次探测后关闭的健康检查 HTTP client 保留 Factory。
- 单例消费者首次解析前完成依赖 override；已解析时须重置相应单例缓存再解析。容器生命周期退出后重置单例，避免重新启动时引用已关闭的旧资源。
- HTTP 通过 `@inject` 与 `Depends(Provide[…])` 注入；MCP 通过显式传入的具体 provider 解析 Use Case，依赖参数不得出现在 Tool schema 中。
- 业务类保持普通构造函数注入，不依赖 Container、Depends 或 Provide。Worker 不再维护独立 factory。
- 数据库共享 session factory，不共享 AsyncSession；session 和事务边界继续由 Repository 管理。
- 启动失败、运行异常或取消均须清理资源；停止消费并等待处理中消息结束后，再关闭数据库、向量库和 Embedding 客户端。
- 测试使用 provider override 并恢复覆盖；HTTP wiring 在应用退出或测试结束时解除。同一进程只运行一个已 wiring 的 HTTP 应用。

验收：容器中不存在 Core 子容器；UseCases 子容器只接收 Services，Services 子容器只接收 Repositories，Repositories 子容器只接收 Resources；HTTP/MCP provider 替换、异步解析、Tool schema、部分启动失败、任务取消、消费退出和原有索引测试均通过。

## 组件职责与依赖方向

> 变更批次：`26-09-27_0`
> 变更来源：`improve-regulations`
> 落地状态：`待实现`
> 实现优先级：`P0`

适用于文档写入、重建、删除和检索主流程。

- 原 `src/rag/interfaces/` 更名为 `src/rag/api/`；HTTP 与 MCP API 只负责协议转换，不包含文档处理、索引或检索业务逻辑。
- 原 `src/rag/core/` 更名为 `src/rag/services/`。每个 Service 按功能拥有独立目录；可选的 `interfaces/` 只定义该 Service 需要稳定约束或替换的依赖接口，可选的 `types/` 只保存该 Service 的 dataclass、Enum 与输入输出类型，不为没有实际接口或类型的 Service 创建空目录。
- 唯一业务依赖路线为 `use_cases -> services -> repositories -> resources`。Use Case 之间绝对不得互相依赖；Service 可以依赖另一个 Service，但应优先保持独立并避免形成循环；Use Case 不得直接访问 Repository，即使简单查询可以由 Repository 独立完成，也必须先由对应 Service 封装。
- Use Case 表示 HTTP、MCP 或 Worker 都可以复用的完整功能点。原 Worker `DocumentIndexer` 改为索引文档 Use Case，由 Ingest/Reindex Handler 调用；Worker 只保留消息消费、Routing Key 分派、重试和失败处理。
- Repository 负责通过 Resource 访问持久化、消息、Embedding 与向量能力；Resource 负责原始外部连接、客户端及其生命周期。Repository 可以导入其所实现或传输的 `services/<name>/interfaces` 与 `services/<name>/types`，不得导入 Service 实现。业务类保持普通构造函数注入，不依赖容器实现。
- FastAPI 进程负责接收请求、解析和切分文档、保存 PostgreSQL 事实数据并向 RabbitMQ 发布索引任务；不得在请求进程中生成 Embedding 或直接写入 Qdrant。
- Python Worker 只通过 RabbitMQ 接收索引任务，并访问 PostgreSQL、Ollama Embedding 和 Qdrant 完成异步索引操作。
- PostgreSQL 是 Document 和 Chunk 的唯一业务事实来源；Qdrant 仅保存可由有效 Chunk 重建的向量索引；RabbitMQ 仅负责消息传输与暂存。
- RAG 服务只负责文档处理、索引和检索，不调用 LLM 生成答案；答案生成由外部 Agent 完成。
- 当前业务最大单位是单个 Document，不建立 Knowledge Base、Collection 业务实体、Document Version 实体或 Index Job 实体。
- 第一版是本地学习系统，不实现认证、授权、多租户、公网部署或任意远程 URL 抓取；`source_uri` 是调用方提供的来源标识，不由服务主动访问。

失败时不得把 RabbitMQ 或 Qdrant 中的临时状态视为业务事实。任何检索结果都必须回到 PostgreSQL 验证对应 Chunk 当前有效。

验收条件：源码与测试不再导入 `rag.interfaces`、`rag.core` 或 `rag.infrastructure`；自动化依赖检查证明 Use Case 不相互导入且不直接导入 Repository 或 Resource，Service 不直接导入 Resource，Repository 除 Service interface/type 契约外只向下依赖 Resource；HTTP、MCP 与 Worker 调用同一组 Use Case；FastAPI 进程没有 Embedding 或 Qdrant 写入路径；删除 Qdrant Collection 后能以 PostgreSQL 数据重新建立索引。

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

权威入口：[`pyproject.toml`](../../pyproject.toml)、[`src/rag/main.py`](../../src/rag/main.py)、[`src/rag/api/http/app.py`](../../src/rag/api/http/app.py) 和 [`src/rag/worker/worker.py`](../../src/rag/worker/worker.py)。

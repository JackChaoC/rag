# HTTP 与 MCP 服务契约

## HTTP API

> 变更批次：`26-09-30_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

第一版提供以下端点：

- `POST /v1/files`：multipart `file`，只保存原文件和 files 记录，返回 `201` 与 `file_id`、`url`、`filename`、`size_bytes`；不创建文档或触发索引。URL 为同源 `/v1/files/{id}`。
- `GET /v1/files/{id}`：在线查看原文件；Markdown/TXT 返回 text/plain，PDF 返回 application/pdf，Content-Disposition 为 inline。
- `GET /v1/files/{id}?download=true`：返回 attachment，前端使用 `<a download>` 发起浏览器下载，保留原始文件名。
- `POST /v1/documents`：JSON `file_url`、必填非空 `title`，可选 `team`、`project`、`description`、`operator`、`metadata`；只接受上传接口返回的文件 URL，不抓取外部 URL；确认发布索引消息后返回 `202`。
- `team` 枚举为 wallet、member、devops、data、event；其他新增字段可空。移除 Source URI 输入和输出，检索引用改用 `file_url`。
- `POST /v1/documents/{document_id}/reindex`：可选 JSON `file_url`；有 URL 时切换到已上传文件，无 URL 时使用现有文件。增加版本、清除旧 Nodes 并发布任务，返回 `202`。原上传文件独立保留。
- `DELETE /v1/documents/{document_id}`：把文档置为 `deleting` 并确认发布 Delete 消息后返回 `202`。
- `GET /v1/documents`：返回文档摘要列表，不返回完整正文。可选 `q` 对标题、项目、操作人、团队和 ID 做不区分大小写的字面子串匹配（`%`、`_` 不作为通配符）；`team`、`status`、`project`、`operator` 精确筛选，各条件以 AND 组合。空白文本忽略，无匹配返回 `[]`；不传参数兼容原列表。筛选在 PostgreSQL 执行。
- `GET /v1/documents/{document_id}/chunks`：按 chunk_index 返回指定文档全部 Chunk。
- `GET /v1/chunks/{chunk_id}`：按 Chunk ID 返回全量内容与来源。
- `GET /v1/documents/{document_id}/chunks/{chunk_id}`：只在 Chunk 属于指定 Document 时返回内容与引用信息。
- `POST /v1/search`：接收 `query` 和 `top_k`，返回 Dense 检索结果，不调用 LLM。
- `GET /health`：分别报告进程存活和 PostgreSQL、RabbitMQ、Qdrant、Ollama 的依赖状态及 worker 消费者/心跳状态；依赖失败时不得仍报告整体 ready。

文档写入响应至少包含 `document_id`、`version`、`status`；搜索结果至少包含 `chunk_id`、`document_id`、`score`、`content`、`file_url`、`title`、`start_line`、`end_line` 和 `metadata`。`top_k` 默认 `5`，HTTP、MCP 和核心检索统一允许 `1..10`。不存在返回 `404`，输入或文件类型不支持返回 `422`，消息未确认或依赖不可用返回 `503`。所有错误使用稳定的 `{ "code": string, "message": string }` 结构。

同一文件 URL 和相同文档信息重复提交返回原文档，并允许重新发布未确认任务；同一文件的不同信息返回 409。文件更新通过 reindex 引用新上传文件。

验收条件：OpenAPI 能表达全部请求响应；接口测试覆盖成功、重复提交、无效 Metadata、不支持格式、未找到和 Publisher Confirm 失败；HTTP 层只调用 Use Case。

## 本地 Web Console

> 变更批次：`26-09-30_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

- FastAPI 在 `/ui/` 同源托管 `frontend/index.html`，不需要独立构建工具、Node 运行时或 CORS 配置。
- Console 覆盖依赖健康、文档录入、列表、文件更新、无文件重建、删除、Dense 检索和 Chunk 精确读取。
- 检索必须显示排名、原始分数、来源、行号、Document ID、Chunk ID 和文本内容；Top-K 控件限制为 `1..10`。
- 异步索引状态自动刷新，依赖失败和 HTTP 错误向用户显示可诊断信息。

验收条件：`GET /ui/` 返回可运行页面；页面能覆盖全部公开 HTTP 端点；`top_k=11` 即使绕过页面也被 HTTP 契约拒绝。

## MCP Tools

> 变更批次：`26-09-19_1`
> 变更来源：`improve-regulations`
> 落地状态：`已实现`
> 实现优先级：`P0`

MCP 使用官方 Python SDK，通过 Streamable HTTP 暴露 `/mcp`，并提供：

- `search_knowledge(query: str, top_k: int = 5)`：返回与 HTTP Search 相同的结构化结果。
- `get_document_chunk(document_id: UUID, chunk_id: UUID)`：返回单个 Chunk 及来源信息。
- `list_documents(q?, team?, status?, project?, operator?)`：与 HTTP 共用文档查询 UseCase，返回相同摘要结构及筛选语义。

MCP 不提供写入、重建、删除或答案生成工具，不提供 `answer_with_sources`。Tool 不复制业务逻辑，必须调用与 HTTP 相同的 Use Case。业务错误转换为可读 Tool Error，不得无限重试或返回伪造结果。

验收条件：MCP 客户端可以发现三个 Tool、调用每个 Tool，并验证其结果与同一 Use Case 的 HTTP 表达一致。

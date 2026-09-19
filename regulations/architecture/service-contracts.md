# HTTP 与 MCP 服务契约

## HTTP API

> 变更批次：`26-09-19_4`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

第一版提供以下端点：

- `POST /v1/documents`：接收 `multipart/form-data`，字段为 `file`、必填 `source_uri`、可选 `title` 和可选 JSON Object 字符串 `metadata`；完成解析和 PostgreSQL 保存并收到 RabbitMQ Publisher Confirm 后返回 `202`。
- `POST /v1/documents/{document_id}/reindex`：接收可选 `multipart/form-data` 文件。提供文件时先按原 Document 的 `source_uri` 解析并替换保存的 Markdown；未提供文件时基于 PostgreSQL 已保存 Markdown 重建。内容或处理配置没有变化时返回当前版本且不创建无效新版本；否则创建下一版本 Chunk，确认发布 Reindex 消息后返回 `202`。
- `DELETE /v1/documents/{document_id}`：把文档置为 `deleting` 并确认发布 Delete 消息后返回 `202`。
- `GET /v1/documents`：返回文档摘要列表，不返回完整正文。
- `GET /v1/documents/{document_id}/chunks/{chunk_id}`：只在 Chunk 属于指定 Document 时返回内容与引用信息。
- `POST /v1/search`：接收 `query` 和 `top_k`，返回 Dense 检索结果，不调用 LLM。
- `GET /health`：分别报告进程存活和 PostgreSQL、RabbitMQ、Qdrant、Ollama 的依赖状态；依赖失败时不得仍报告整体 ready。

文档写入响应至少包含 `document_id`、`version`、`status`；搜索结果至少包含 `chunk_id`、`document_id`、`score`、`content`、`source_uri`、`title`、`start_line`、`end_line` 和 `metadata`。`top_k` 默认 `5`，HTTP、MCP 和核心检索统一允许 `1..10`。不存在返回 `404`，输入或文件类型不支持返回 `422`，消息未确认或依赖不可用返回 `503`。所有错误使用稳定的 `{ "code": string, "message": string }` 结构。

同一 `source_uri` 与相同内容重复提交必须返回原 Document/版本并安全重新发布尚未确认的任务；相同 `source_uri` 与不同内容必须通过带文件的 Reindex 更新，不得由创建端点静默覆盖。

验收条件：OpenAPI 能表达全部请求响应；接口测试覆盖成功、重复提交、无效 Metadata、不支持格式、未找到和 Publisher Confirm 失败；HTTP 层只调用 Use Case。

## 本地 Web Console

> 变更批次：`26-09-19_4`
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
- `list_documents()`：返回与 HTTP 文档列表相同的摘要结构。

MCP 不提供写入、重建、删除或答案生成工具，不提供 `answer_with_sources`。Tool 不复制业务逻辑，必须调用与 HTTP 相同的 Use Case。业务错误转换为可读 Tool Error，不得无限重试或返回伪造结果。

验收条件：MCP 客户端可以发现三个 Tool、调用每个 Tool，并验证其结果与同一 Use Case 的 HTTP 表达一致。

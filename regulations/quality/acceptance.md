# 基础 RAG 链路验收

## 自动化验证范围

> 变更批次：`26-09-20_0`
> 变更来源：`improve-regulations`
> 落地状态：`已实现`
> 实现优先级：`P0`

实现本批次时必须提供以下可重复验证，不以手工观察代替：

- 单元测试：Parser 接口、Cleaner 确定性、Markdown 结构切块、Chunk 行号和 Hash 稳定性。
- 数据库测试：Document/Chunk 约束、级联禁止、版本顺序唯一性、有效状态查询。
- 消息测试：Routing Key、Publisher Confirm 失败、手动 ACK、有限重试、退避和死信。
- Worker 集成测试：Ingest、Reindex、Delete 的成功路径、重复投递、过期版本、Ollama 失败、Qdrant 部分成功和 PostgreSQL 状态切换失败。
- 检索集成测试：Query Embedding、Qdrant 搜索、PostgreSQL 批量回填、排名恢复、无效 Point 过滤和有界 over-fetch。
- 端到端测试：至少一种非 Markdown 文件完成解析、持久化、异步 Embedding、向量写入和带来源检索；解析失败不发布消息、不产生残留向量。
- 可重建性测试：清空 `rag_chunks` 后，从 PostgreSQL 有效 Chunk 重建，Point ID 集合与预期一致。
- 接口契约测试：FastAPI OpenAPI、HTTP 状态码与错误结构、MCP Tool 发现和三个 Tool 调用。

测试必须使用可控替身覆盖外部失败，并提供 Docker Compose 启动真实 PostgreSQL、RabbitMQ 和 Qdrant 的本地集成验证路径。真实 Ollama 可以在日常测试中使用替身，但 PDF 端到端验收必须使用本地 `qwen3-embedding:8b`，并记录实际模型、向量维度和距离度量。

本批次只有在相关产品代码、SQLAlchemy Model、Alembic migration 和测试全部实现，且上述验证通过后，才能由 `implement-regulations` 将状态改为“已实现”。仅创建目录、接口或空测试不满足验收条件，也不得更新 `target.md` 的学习进度。

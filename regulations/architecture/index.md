# 架构与接口边界

## 权威内容

- RAG 服务、Worker、PostgreSQL、RabbitMQ、Ollama Embedding 和 Qdrant 的职责边界。
- 同步请求与异步索引之间的总体数据流。
- 数据事实来源和可重建数据的归属。
- Python 运行时基础设施选型和 Prisma migration 策略。
- HTTP 端点与 MCP Tool 的公开输入输出契约。

## 明确不包含

- PostgreSQL 的字段和约束。
- RabbitMQ Exchange、Queue 和重试参数。
- Worker 内部状态转换步骤。
- PostgreSQL table 的目标 DDL。
- RabbitMQ Retry Queue 的具体拓扑。

## 具体规范

- [系统边界与数据所有权](system-boundaries.md)
- [运行时与 Migration 策略](runtime-and-migrations.md)
- [HTTP 与 MCP 服务契约](service-contracts.md)

# Worker 幂等与状态转换

## 权威内容

- Ingest、Reindex、Delete 消息的处理步骤和成功终态。
- 同一消息重复消费、过期版本和部分失败的处理。
- PostgreSQL 与 Qdrant 跨系统操作的补偿边界。

## 明确不包含

- RabbitMQ 拓扑和消息持久化配置。
- PostgreSQL 表字段。
- Qdrant 搜索结果排序。

## 具体规范

- [索引生命周期与幂等](indexing-lifecycle.md)


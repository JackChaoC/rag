# LlamaIndex 分支验收

## 自动化覆盖

> 变更批次：`26-09-30_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

- 保留 main 的切分规则测试；新增 NodeParser 的全局 index、H1/H2 metadata、稳定 ID 与默认 Embedding 输入测试。
- Reader 实测 Markdown/PDF；FileRepository 覆盖原文件存储、删除与路径穿越拒绝。
- 本地真实 Qdrant SDK + 官方 LlamaIndex 适配器测试完整 Node 往返、排序、查询、删除及 Collection 删除后重建；Embedding 替身仅用于日常快速测试。
- API 测试覆盖 OpenAPI、错误格式、新增 Chunk GET、旧 HTTP/MCP 契约、Tool schema 与依赖替换。
- Worker 覆盖重复索引/删除、旧任务无操作、状态切换失败后重试、终态清理；Broker 覆盖 retry、dead-letter、ACK 与退出等待。
- 容器覆盖共享依赖、资源逆序关闭、启动失败/取消、HTTP/MCP 使用同一 provider；架构测试禁止跨层导入。
- 显式 RUN_RAG_INTEGRATION=1 启用真实 PostgreSQL、RabbitMQ、Qdrant、Ollama：文档约束/跨连接锁、PDF 到检索/更新/重建/删除、真实延迟重试。
- 文件分离迁移需验证有数据的旧库，保留文件和索引；alembic check 无结构差异。
- 不更新学习阶段完成度，不把架构重构等同于完成 Agent 学习。

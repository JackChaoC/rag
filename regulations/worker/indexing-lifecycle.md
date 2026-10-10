# Worker 生命周期

## 索引、更新、删除与失败

> 变更批次：`26-09-30_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

- API/Worker 通过 PG transaction advisory lock 对同一 document_id 串行化；创建文档按 file_id 另加锁防止重复创建。
- Worker 先读当前 Document：旧版本消息直接成功返回，不删除新 Nodes；超前版本失败；deleting/deleted 不再索引。
- Ingest/Reindex：置 indexing → 删除该文档旧 Nodes → 从 file_path 读取 → splitter → Embedding → Qdrant 写入 → ready，成功清空 last_error，最后 Broker ACK。
- 重复消息使用相同 Node ID，重试会清理该文档残留并重新生成。Qdrant 成功但状态更新失败也可重试收敛。
- Reindex API 引用已上传的新文件（或当前文件）并更新 PG 后删除旧 Nodes，再发布新版本；无新 URL 时保留当前文件并创建下一版本，不承诺更新期间可搜索。
- Delete API 置 deleting 并发布任务；Worker 删除该文档 Nodes，保留独立上传的原文件，置 deleted。重复删除幂等。
- 索引终态失败清理当前文档 Nodes 并记 failed/last_error；删除终态失败保持 deleting/last_error，禁止旧 ingest 消息复活文档，可重试 DELETE。
- RebuildIndexUseCase 为 ready/failed 文档发布当前版本重建任务，返回排队文档数；不调用其他 UseCase，不新建版本。

## Dispatcher 与 Handler

> 变更批次：`26-09-30_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

- worker.py 是消费入口；dispatcher.py 使用 match routing_key。
- document.ingest / document.reindex / document.delete 分别对应独立 DocumentIngestHandler / DocumentReindexHandler / DocumentDeleteHandler；不相互继承。
- Ingest/Reindex Handler 复用 IndexDocumentUseCase，而不是共用一个 handler。
- Dispatcher 验证 routing_key 与 operation 一致；ACK、重试、死信仍归 Broker。

## Worker 健康检查

- 注册消费者后每 10 秒向同 namespace 的 worker-heartbeat 队列发送心跳；RabbitMQ TTL 为 30 秒，最多保留一条。
- `/health` 的 `dependencies.worker` 同时要求有效心跳和 jobs 队列至少一个消费者，否则整体 ready=false，返回 503。
- 多 worker 时检查至少一个存活消费者，不表示每个 worker 或单条任务均健康；心跳发送失败退出 worker。

- 可重试索引失败保持 pending 并保留异常类型和详情；只有重试耗尽才标记 failed。

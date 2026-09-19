# 索引任务拓扑与投递语义

## Broker 拓扑与消息契约

> 变更批次：`26-09-19_3`
> 变更来源：`improve-regulations`
> 落地状态：`已实现`
> 实现优先级：`P0`

- 使用 durable direct exchange `rag.indexing`。
- durable queue `rag.indexing.jobs` 绑定 `document.ingest`、`document.reindex`、`document.delete` 三个首次投递 Routing Key，并绑定 `retry.1`、`retry.2`、`retry.3` 三个延迟回流 Routing Key。
- durable direct dead-letter exchange `rag.indexing.dlx` 与 durable queue `rag.indexing.dead` 用于隔离超过重试上限或不可恢复的消息。
- durable direct retry exchange `rag.indexing.retry` 绑定 `rag.indexing.retry.1`、`rag.indexing.retry.2`、`rag.indexing.retry.3` 三个 durable Retry Queue；默认 TTL 分别为 `1s`、`5s`、`30s`。Worker 按尝试次数使用 `retry.1`、`retry.2` 或 `retry.3` 投递，Retry Queue 到期后由 Dead-letter Exchange 保留该 Routing Key 回流 `rag.indexing.jobs`。原 operation Routing Key 写入 `x-original-routing-key` Header，业务意图仍以消息体中经枚举校验的 `operation` 为准；不得依赖 Retry Queue 动态改写 dead-letter routing key。
- 生产者使用持久消息并开启 Publisher Confirms；收到 Broker Confirm 前不得向调用方报告任务已提交。
- 消费者使用手动 ACK 和有界 `prefetch_count`；只有业务操作达到对应成功终态后才能 ACK。
- 消息体只包含 `document_id`、`operation`、`version`；重试次数放在消息 Header。不得传输 Document 正文、Chunk 内容或向量。
- 每条消息必须可由 `(document_id, operation, version)` 唯一描述其业务意图，重复投递不得产生不同 Point ID 或额外版本。

可恢复错误最多重试三次。Worker 根据 `x-retry-count` 选择下一档 Retry Queue，Publisher Confirm 成功后 ACK 原消息；禁止对原队列立即 `nack(requeue=true)`。不可恢复错误或第三次重试仍失败的消息发布到 `rag.indexing.dlx`，Confirm 成功后 ACK 原消息，并由 Worker 将 Document 标记为 `failed`、写入 `last_error`。重试延迟允许通过配置覆盖，但队列数量和最大重试次数第一版固定为三次。

发布失败时，请求必须返回可识别的失败，不得伪装为已提交；已经保存为 `pending` 但未确认发布的文档必须允许调用方使用相同 `source_uri` 和内容安全重试，重试不得新建重复 Document 或版本。

验收条件：自动化测试证明 durable 声明和路由正确；未 ACK 消息会重投；重复消息保持幂等；重试达到上限后进入死信队列；Publisher Confirm 失败不会返回成功。

Worker 的成功终态与版本防护由 [`worker/indexing-lifecycle.md`](../worker/indexing-lifecycle.md) 定义。

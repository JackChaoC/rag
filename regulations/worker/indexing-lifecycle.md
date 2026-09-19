# 索引生命周期与幂等

## 版本防护与操作顺序

> 变更批次：`26-09-19_0`
> 变更来源：`improve-regulations`
> 落地状态：`已实现`
> 实现优先级：`P0`

Worker 处理消息前必须读取 PostgreSQL 中的 Document 和目标版本 Chunk，不信任消息携带业务正文。消息版本落后于 `documents.current_version` 时视为过期任务：不得改变当前版本状态或向量；清理能够明确归属于过期版本的 Point 后 ACK。消息版本高于当前版本时属于状态不一致，必须失败并保留诊断信息。

Ingest 与 Reindex 必须按以下顺序执行：

1. 以条件更新把匹配版本的 Document 从可处理状态改为 `indexing`，防止并发 Worker 同时取得所有权。
2. 查询目标版本全部 Chunk，并为每个 Chunk 生成 Embedding。
3. 使用 `chunks.id` 作为 Qdrant Point ID 执行幂等 Upsert。
4. 仅当目标版本全部 Point 写入成功后，在同一 PostgreSQL 事务中启用目标版本 Chunk、停用旧版本 Chunk，并把 Document 置为 `ready`、清空 `last_error`。
5. 根据 PostgreSQL 中的旧 Chunk ID 物理删除旧 Qdrant Point；重复删除不存在的 Point 视为成功。
6. 完成上述成功路径后 ACK。

Delete 必须先把 Document 置为 `deleting`；Worker 根据该 Document 的全部 Chunk ID 幂等删除 Qdrant Point，随后在 PostgreSQL 事务中停用 Chunk、把 Document 置为 `deleted` 并清空 `last_error`，最后 ACK。已处于 `deleted` 且 Point 已不存在时重复 Delete 直接视为成功。

如果 Qdrant Upsert 成功但 PostgreSQL 状态切换失败，消息必须重试；相同 Chunk ID 的重复 Upsert 覆盖原 Point。目标版本最终失败时，Worker 必须尽力删除该版本所有 Point，再把 Document 置为 `failed` 并记录 `last_error`。不得将旧版本重新标记为新版本。

同一 Document 进入 `deleting` 后不得接受新的 Ingest 或 Reindex，除非后续规范显式定义恢复流程。

验收条件：对每种 operation 重复投递至少两次，数据库版本、有效 Chunk 数量和 Qdrant Point 数量不增加；乱序旧版本不会覆盖新版本；任一步骤注入失败后重试能够收敛到唯一成功或失败终态。
